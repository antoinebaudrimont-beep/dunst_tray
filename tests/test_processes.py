from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from dunst_tray.activation import ActivationError, DesktopWindowActivator
from dunst_tray.applications import ApplicationCatalog, DesktopApplication
from dunst_tray.processes import (
    ProcessIdentity, descends_from, process_snapshot, terminal_matches,
)
from test_activation import notification


def process(pid, parent, tty=0, foreground=0, executable=""):
    return ProcessIdentity(pid, parent, pid, tty, foreground, executable)


class TerminalIdentityTests(unittest.TestCase):
    def test_snapshot_parsing_is_bounded_and_never_reads_command_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "12"
            directory.mkdir()
            (directory / "stat").write_text("12 (ignored ) name) S 10 12 12 7 12 0")
            (directory / "exe").symlink_to("/synthetic/bin/mail-client")
            snapshot = process_snapshot(root)
            self.assertEqual(snapshot[12].executable, "mail-client")
            self.assertEqual(snapshot[12].parent, 10)
            with self.assertRaises(ValueError):
                process_snapshot(root, limit=0)
            (directory / "stat").write_text("malformed")
            with self.assertRaises(ValueError):
                process_snapshot(root)

    def setUp(self):
        self.processes = {10: process(10, 1), 11: process(11, 10, 7, 12),
                          12: process(12, 11, 7, 12, "synthetic-mail")}

    def test_foreground_owner_not_title_or_background_program(self):
        self.assertTrue(terminal_matches(10, "synthetic-mail", self.processes))
        self.assertFalse(terminal_matches(10, "different-program", self.processes))
        self.assertFalse(terminal_matches(99, "synthetic-mail", self.processes))
        self.processes[12] = replace(self.processes[12], foreground_group=11)
        self.assertFalse(terminal_matches(10, "synthetic-mail", self.processes))

    def test_multiple_tabs_multiplexers_and_foreign_owners_are_rejected(self):
        self.processes[20] = process(20, 10, 8, 20, "shell")
        self.assertFalse(terminal_matches(10, "synthetic-mail", self.processes))
        del self.processes[20]
        self.processes[10] = replace(self.processes[10], owner=os.geteuid() + 1)
        self.assertFalse(terminal_matches(10, "synthetic-mail", self.processes))
        self.processes[10] = process(10, 1)
        self.processes[12] = replace(self.processes[12], owner=os.geteuid() + 1)
        self.assertFalse(terminal_matches(10, "synthetic-mail", self.processes))

    def test_ancestry_cycles_and_incomplete_snapshots_fail_closed(self):
        self.assertTrue(descends_from(12, 10, self.processes))
        self.processes[11] = replace(self.processes[11], parent=12)
        self.assertFalse(descends_from(12, 10, self.processes))
        del self.processes[11]
        self.assertFalse(descends_from(12, 10, self.processes))

    def activator(self, windows=("0x1",), host=None):
        self.focused = []
        catalog = ApplicationCatalog([])
        catalog.applications.append(DesktopApplication(
            "org.example.Mail", "Synthetic Mail", "", frozenset({"mail-ui"}),
            "synthetic-mail", True,
        ))

        def run(arguments):
            if arguments[-1] == "-l":
                output = "\n".join(f"{window} 0 host misleading-title" for window in windows)
            elif arguments[-1] == "WM_CLASS":
                output = 'WM_CLASS(STRING) = "kitty", "kitty"'
            elif arguments[-1] == "WM_CLIENT_MACHINE":
                output = ('_NET_WM_PID(CARDINAL) = 10\n'
                          f'WM_CLIENT_MACHINE(STRING) = "{host or socket.gethostname()}"')
            else:
                self.focused.append(tuple(arguments))
                output = ""
            return subprocess.CompletedProcess(arguments, 0, output, "")
        return DesktopWindowActivator(catalog, processes=lambda: self.processes,
                                      wmctrl="wmctrl", xprop="xprop", display=":0",
                                      runner=run)

    def test_unique_terminal_focus_without_default_action(self):
        activator = self.activator()
        item = replace(notification("Synthetic Mail"), actions=())
        activator.activate(item)
        self.assertIn(("wmctrl", "-i", "-a", "0x1"), self.focused)

    def test_shared_terminal_server_multiple_windows_and_remote_pid_rejected(self):
        for activator in (self.activator(("0x1", "0x2")),
                          self.activator(host="different-machine.invalid")):
            with self.assertRaises(ActivationError):
                activator.activate(notification("Synthetic Mail"))
        self.assertEqual(self.focused, [])

    def test_ambiguous_desktop_names_and_invalid_explicit_hint_never_fallback(self):
        activator = self.activator()
        activator.catalog.applications.append(DesktopApplication(
            "org.other.Mail", "Synthetic Mail", "", frozenset({"kitty"}),
        ))
        self.assertIsNone(activator.identity(notification("Synthetic Mail")))
        self.assertIsNone(activator.identity(replace(
            notification("kitty"), desktop_entry="does-not-exist")))
