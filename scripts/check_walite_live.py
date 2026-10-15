#!/usr/bin/env python3
"""Opt-in real-X11 navigation acceptance, synthetic Walite only.

Stop the normal tray and Walite first. Build tests/fixtures/walite_navigation_test.go
in an isolated archive of Walite 77459fd (see docs/WALITE.md), then launch that
fixture in an X11 terminal. This script takes its private directory and numeric
window ID. It uses temporary filtered history, physically clicks GTK controls,
never connects to WhatsApp, and never changes DND or clears daemon history.
The fixture is stopped in the final negative test. Restore normal apps afterward.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path

from check_live import active_window, spin, SyntheticHistory, ProtectedDunst
from dunst_tray.capture import NotificationMonitor
from dunst_tray.config import AppConfig
from dunst_tray.history import HistoryStore
from dunst_tray.ui import Gtk, TrayApplication

PREFIX = "DunstTrayWaliteFixture:"


class FixtureHistory(SyntheticHistory):
    def add(self, notification):
        if notification.app_name != "walite" or not notification.summary.startswith(PREFIX):
            return -1
        return HistoryStore.add(self, notification)


def click(widget):
    spin(lambda: widget.get_mapped())
    top = widget.get_toplevel()
    for _ in range(8):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.01)
    x, y = widget.translate_coordinates(top, 0, 0)
    allocation = widget.get_allocation()
    subprocess.run([
        "xdotool", "mousemove", "--sync", "--window",
        str(top.get_window().get_xid()),
        str(x + allocation.width // 2), str(y + allocation.height // 2),
        "click", "1",
    ], check=True)


def run(directory, window):
    pid = int((directory / "fixture.pid").read_text())
    original_focus = active_window()
    original_pause = ProtectedDunst()._run("get-pause-level")
    if original_pause != "0":
        raise RuntimeError("Resume notifications before this opt-in check")
    tray = monitor = history = None
    try:
        with tempfile.TemporaryDirectory(prefix="dunst-walite-acceptance-") as temporary:
            folder = Path(temporary)
            history = FixtureHistory(folder / "history.sqlite3")
            tray = TrayApplication(replace(AppConfig(), panel_width=280),
                                   folder / "config.ini", history,
                                   ProtectedDunst(), lambda: None)
            monitor = NotificationMonitor(history, tray.notification_received)
            monitor.start()
            spin(lambda: tray.status_icon.is_embedded())

            def state():
                return (directory / "screen.state").read_text()

            def focus_fixture():
                subprocess.run(["wmctrl", "-i", "-a", window], check=True)
                spin(lambda: int(active_window(), 16) == int(window, 16))

            def key(*arguments):
                subprocess.run(["xdotool", *arguments], check=True)
                time.sleep(0.15)

            def send(group):
                count = history.count()
                os.kill(pid, signal.SIGUSR2 if group else signal.SIGUSR1)
                spin(lambda: history.count() == count + 1)
                item = history.latest()
                assert item.walite_activation is not None
                return item.id

            def button(row_id, label):
                if not tray.window.get_visible():
                    tray.toggle_center()
                tray.refresh()
                # Let the capture callback's coalesced refresh finish before
                # retaining a physical widget reference for the mouse click.
                for _ in range(8):
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    time.sleep(0.01)
                card = tray.groups_box.get_children()[0]
                if not card.expanded:
                    card._toggle(None)
                for item, message in zip(card.notifications, card.messages.get_children()):
                    if item.id == row_id:
                        footer = message.get_children()[-1]
                        controls = footer.get_children()[-1]
                        return next(child for child in controls.get_children()
                                    if isinstance(child, Gtk.Button)
                                    and child.get_label() == label)
                raise AssertionError("Synthetic row/control missing")

            spin(lambda: state() == "DIRECT")
            group_id = send(True)
            direct_id = send(False)  # Older group must retain its own target.
            show = button(group_id, "Show app")
            click(show)
            spin(lambda: int(active_window(), 16) == int(window, 16))
            assert state() == "DIRECT"
            assert all(item.walite_activation for item in history.all())
            print("PASS physical Show app focuses without navigating/consuming", flush=True)

            for row_id, expected in ((group_id, "GROUP"), (direct_id, "DIRECT")):
                control = button(row_id, "Open discussion")
                assert control.get_sensitive()
                spin(lambda: tray.window.get_size()[0] == 280)
                click(control)
                spin(lambda: state() == expected)
                spin(lambda: int(active_window(), 16) == int(window, 16))
                assert next(item for item in history.all() if item.id == row_id).walite_activation is None
                print(f"PASS physical retained {expected} navigation, real TUI and X11 focus", flush=True)
            assert history.count() == 2
            assert history.unread_count() == 0

            draft_id = send(True)
            focus_fixture()
            key("key", "Return")
            key("type", "--clearmodifiers", "unsent-fixture-draft")
            spin(lambda: state() == "DIRECT DRAFT")
            click(button(draft_id, "Open discussion"))
            spin(lambda: int(active_window(), 16) == int(window, 16))
            time.sleep(0.3)
            assert state() == "DIRECT DRAFT"
            key("key", "Escape")
            print("PASS real composing draft preserved; no message sent", flush=True)

            modal_id = send(True)
            focus_fixture()
            key("key", "ctrl+p")
            click(button(modal_id, "Open discussion"))
            spin(lambda: int(active_window(), 16) == int(window, 16))
            key("key", "Escape")
            spin(lambda: state().startswith("DIRECT"))
            print("PASS modal protection retains original discussion", flush=True)

            unavailable_id = send(True)
            os.kill(pid, signal.SIGTERM)
            spin(lambda: not (directory / "fixture.pid").exists())
            control = button(unavailable_id, "Open discussion")
            assert not control.get_sensitive()
            assert history.count() == 5
            assert ProtectedDunst()._run("get-pause-level") == original_pause
            print("PASS exited receiver disabled, history retained, DND unchanged", flush=True)
    finally:
        if monitor:
            monitor.stop()
        if tray:
            tray.destroy()
        if history:
            history.close()
        subprocess.run(["wmctrl", "-i", "-a", original_focus], check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_directory", type=Path)
    parser.add_argument("fixture_window", type=lambda value: hex(int(value, 0)))
    arguments = parser.parse_args()
    run(arguments.fixture_directory, arguments.fixture_window)
