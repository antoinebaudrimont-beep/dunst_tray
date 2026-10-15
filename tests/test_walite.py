from __future__ import annotations

import json
import os
import queue
import socket
import tempfile
import threading
import time
import traceback
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from dunst_tray.history import HistoryStore
from dunst_tray.protocol import parse_notify_call
from dunst_tray.walite import (
    WaliteActivation, WaliteActivationClient, WaliteActivationError,
    parse_activation,
)
from test_activation import notification


def hint(endpoint="/tmp/walite-activation-synthetic/s-synthetic.sock", **changes):
    value = {"version": 1, "activation_socket": endpoint,
             "activation_id": "a" * 64}
    value.update(changes)
    return json.dumps(value)


class WaliteHintTests(unittest.TestCase):
    def test_valid_hint_is_private_and_only_retained_for_walite(self):
        raw = hint()
        for app, expected in (("walite", True), ("Other app", False)):
            parsed = parse_notify_call((app, 0, "", "Synthetic", "Body", [],
                                        {"x-walite-activation": raw}, 1))
            self.assertEqual(parsed.walite_activation is not None, expected)
            self.assertNotIn("activation_id", repr(parsed))
            self.assertNotIn("walite-activation", repr(parsed))
        self.assertEqual(repr(parse_activation(raw)), "WaliteActivation()")

    def test_malformed_unknown_and_identity_bearing_metadata_is_ignored(self):
        invalid = (
            None, {}, "", "null", "[]", "{", hint(version=True),
            hint(version=2), hint(activation_id="A" * 64),
            hint(activation_id="a" * 63), hint(chat_id="synthetic@lid"),
            hint(token="synthetic-legacy-credential"),
            hint(endpoint="/tmp/unrelated.sock"),
            hint(endpoint="/tmp/walite-activation-x/../s-x.sock"),
            hint(endpoint="\x00abstract"), hint(activation_socket=123),
            hint(endpoint="/tmp/walite-activation-" + "x" * 100 + "/s-x.sock"),
            '{"version":1,"version":1,"activation_socket":"x",'
            '"activation_id":"' + "a" * 64 + '"}',
            " " * 1025,
        )
        for raw in invalid:
            with self.subTest(index=invalid.index(raw)):
                self.assertIsNone(parse_activation(raw))


class WaliteSocketTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="walite-activation-")
        self.directory = Path(self.temporary.name)
        self.endpoint = self.directory / "s-synthetic.sock"
        self.metadata = parse_activation(hint(str(self.endpoint)))
        self.assertIsNotNone(self.metadata)
        self.client = WaliteActivationClient(timeout=0.2)
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(str(self.endpoint))
        self.listener.listen(1)
        self.listener.settimeout(0.5)
        self.endpoint.chmod(0o600)
        self.received = queue.Queue()
        self.reader = None

    def receive(self):
        def read():
            try:
                connection, _address = self.listener.accept()
                with connection:
                    connection.settimeout(0.5)
                    payload = bytearray()
                    while True:
                        block = connection.recv(4096)
                        if not block:
                            break
                        payload.extend(block)
                    self.received.put(bytes(payload))
            except (OSError, TimeoutError):
                self.received.put(None)
        self.reader = threading.Thread(target=read)
        self.reader.start()

    def tearDown(self):
        self.listener.close()
        if self.reader:
            self.reader.join(timeout=1)
            self.assertFalse(self.reader.is_alive())
        self.directory.chmod(0o700)
        self.temporary.cleanup()

    def test_native_socket_writes_exact_object_then_eof_without_waiting_for_ack(self):
        self.receive()
        started = time.monotonic()
        self.client.send(self.metadata)
        self.assertLess(time.monotonic() - started, 0.4)
        payload = self.received.get(timeout=1)
        self.assertEqual(payload, b'{"version":1,"activation_id":"' +
                         b"a" * 64 + b'"}')
        self.assertNotIn(b"chat_id", payload)
        self.assertNotIn(b"activation_socket", payload)

    def test_private_ownership_modes_and_socket_type_are_required(self):
        self.assertTrue(self.client.availability(self.metadata)[0])
        for mode in (0o755, 0o750, 0o777):
            self.directory.chmod(mode)
            self.assertFalse(self.client.availability(self.metadata)[0])
        self.directory.chmod(0o700)
        self.endpoint.chmod(0o644)
        self.assertFalse(self.client.availability(self.metadata)[0])
        self.endpoint.chmod(0o600)
        with patch("dunst_tray.walite.os.geteuid", return_value=os.geteuid() + 1):
            self.assertFalse(self.client.availability(self.metadata)[0])
        self.listener.close()
        self.endpoint.unlink()
        self.endpoint.write_text("synthetic non-socket", encoding="utf-8")
        self.endpoint.chmod(0o600)
        self.assertFalse(self.client.availability(self.metadata)[0])

    def test_symlink_socket_and_parent_are_rejected(self):
        other = self.directory / "s-other.sock"
        self.endpoint.rename(other)
        self.endpoint.symlink_to(other)
        self.assertFalse(self.client.availability(self.metadata)[0])
        with tempfile.TemporaryDirectory(prefix="walite-activation-") as alias:
            alias_path = Path(alias)
            alias_path.rmdir()
            alias_path.symlink_to(self.directory, target_is_directory=True)
            try:
                value = parse_activation(hint(str(alias_path / "s-other.sock")))
                self.assertFalse(self.client.availability(value)[0])
            finally:
                alias_path.unlink()

    def test_refused_and_missing_endpoints_have_redacted_errors(self):
        self.listener.close()
        for remove in (False, True):
            if remove:
                self.endpoint.unlink()
            try:
                self.client.send(self.metadata)
                self.fail("unavailable endpoint unexpectedly accepted")
            except WaliteActivationError as error:
                rendered = "".join(traceback.format_exception(error))
                self.assertNotIn(str(self.endpoint), rendered)
                self.assertNotIn(self.metadata.activation_id, rendered)

    def test_socket_replacement_after_connect_is_rejected_before_writing(self):
        self.receive()
        original_stat = os.stat
        calls = 0

        def replacing_stat(*args, **kwargs):
            nonlocal calls
            result = original_stat(*args, **kwargs)
            if kwargs.get("dir_fd") is not None:
                calls += 1
                if calls == 2:
                    values = list(result)
                    values[1] += 1
                    return os.stat_result(values)
            return result

        with patch("dunst_tray.walite.os.stat", side_effect=replacing_stat):
            with self.assertRaises(WaliteActivationError):
                self.client.send(self.metadata)
        self.assertEqual(self.received.get(timeout=1), b"")

    def test_wrong_peer_uid_is_rejected_before_writing(self):
        import struct
        self.receive()
        original_socket = socket.socket

        class WrongPeer:
            def __enter__(wrapper):
                wrapper.connection = original_socket(socket.AF_UNIX,
                                                     socket.SOCK_STREAM)
                return wrapper

            def __exit__(wrapper, *_args):
                wrapper.connection.close()

            def __getattr__(wrapper, name):
                return getattr(wrapper.connection, name)

            def getsockopt(wrapper, *_args):
                return struct.pack("3i", 1, os.geteuid() + 1, os.getegid())

        with patch("dunst_tray.walite.socket.socket", return_value=WrongPeer()):
            with self.assertRaises(WaliteActivationError):
                self.client.send(self.metadata)
        self.assertEqual(self.received.get(timeout=1), b"")


class WaliteHistoryIntegrationTests(unittest.TestCase):
    def test_migration_roundtrip_consumption_and_clear_preserve_record_state(self):
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "history.sqlite3"
            store = HistoryStore(location)
            store.add(notification("walite"))
            store._connection.execute(
                "ALTER TABLE notifications DROP COLUMN walite_activation_json"
            )
            store._connection.commit()
            store.close()
            store = HistoryStore(location)
            self.assertIsNone(store.latest().walite_activation)
            item = replace(notification("walite"),
                           walite_activation=parse_activation(hint()),
                           received_at=2)
            store.add(item)
            store.close()
            store = HistoryStore(location)
            retained = store.latest()
            self.assertEqual(retained.walite_activation, item.walite_activation)
            self.assertTrue(retained.unread)
            self.assertEqual(len(store.grouped()["walite"]), 2)
            self.assertTrue(store.take_walite_activation(retained))
            self.assertFalse(store.take_walite_activation(retained))
            self.assertIsNone(store.latest().walite_activation)
            self.assertEqual(store.count(), 2)
            self.assertEqual(store.unread_count(), 2)
            store.clear()
            self.assertEqual(store.unread_count(), 0)
            store.close()

    def test_retention_removes_capability_with_its_notification(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HistoryStore(Path(directory) / "history.sqlite3", limit=1)
            store.add(replace(notification(),
                              walite_activation=parse_activation(hint())))
            store.add(replace(notification(), received_at=2))
            self.assertIsNone(store.latest().walite_activation)
            store.close()
