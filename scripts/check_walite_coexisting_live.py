#!/usr/bin/env python3
"""Synthetic production-TUI regression without stopping the real Walite.

Stop only the normal tray. Launch the existing offline Walite fixture (see
WALITE.md), then pass its directory. Both Walite windows remain marked, so
production focus resolution MUST reject ambiguity; navigation still uses the
exact notification socket. No account client, real chat or message sending.
The fixture is terminated by this test; normal Walite is never signalled.
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
from unittest.mock import patch

from check_live import ProtectedDunst, active_window, spin
from check_walite_live import FixtureHistory, click
from dunst_tray.capture import NotificationMonitor
from dunst_tray.config import AppConfig
from dunst_tray.ui import Gtk, TrayApplication


def run(directory):
    spin(lambda: (directory / "fixture.pid").exists()
         and (directory / "screen.state").exists())
    pid = int((directory / "fixture.pid").read_text())
    original_focus = active_window()
    original_pause = ProtectedDunst()._run("get-pause-level")
    tray = monitor = history = None
    try:
        with tempfile.TemporaryDirectory(prefix="dunst-walite-coexisting-") as temporary:
            folder = Path(temporary)
            history = FixtureHistory(folder / "history.sqlite3")
            tray = TrayApplication(replace(AppConfig(), auto_hide=True,
                                          auto_hide_timeout=3),
                                   folder / "config.ini", history,
                                   ProtectedDunst(), lambda: None)
            monitor = NotificationMonitor(history, tray.notification_received)
            monitor.start()
            spin(lambda: tray.status_icon.is_embedded())

            def button(row_id, label):
                if not tray.window.get_visible():
                    tray.toggle_center()
                tray.refresh()
                deadline = time.monotonic() + .15
                spin(lambda: time.monotonic() >= deadline)
                card = tray.groups_box.get_children()[0]
                if not card.expanded:
                    click(card.header)
                    deadline = time.monotonic() + .15
                    spin(lambda: time.monotonic() >= deadline)
                for item, message in zip(card.notifications, card.messages.get_children()):
                    if item.id == row_id:
                        controls = message.get_children()[-1].get_children()[-1]
                        return next(child for child in controls.get_children()
                                    if isinstance(child, Gtk.Button)
                                    and child.get_label() == label)
                raise AssertionError("Fixture row not found")

            os.kill(pid, signal.SIGUSR2)
            spin(lambda: history.count() == 1)
            group_id = history.latest().id
            os.kill(pid, signal.SIGUSR1)
            spin(lambda: history.count() == 2)
            direct_id = history.latest().id
            assert not button(group_id, "Show app").get_sensitive()
            print("PASS two marked Walite windows: generic focus safely disabled", flush=True)

            def navigate(row_id, expected):
                previous = next(item for item in history.all() if item.id == row_id)
                control = button(row_id, "Open discussion")
                assert control.get_sensitive()
                with patch.object(tray.walite, "raise_window",
                                  wraps=tray.walite.raise_window) as raised:
                    click(control)
                    spin(lambda: (directory / "screen.state").read_text() == expected
                         and not tray.window.get_visible())
                    raised.assert_not_called()
                renewed = next(item for item in history.all() if item.id == row_id)
                assert renewed.walite_activation != previous.walite_activation
                assert renewed.walite_activation.expires_at == previous.walite_activation.expires_at
                assert history.count() == 2
                assert button(row_id, "Open discussion").get_sensitive()
                tray.window.hide()

            for row_id, expected in ((group_id, "GROUP"), (direct_id, "DIRECT"),
                                     (group_id, "GROUP"), (group_id, "GROUP"),
                                     (direct_id, "DIRECT")):
                navigate(row_id, expected)
            assert history.unread_count() == 0
            assert ProtectedDunst()._run("get-pause-level") == original_pause
            print("PASS physical repeated/alternating v2 navigation with auto-hide enabled", flush=True)
            print("PASS real synthetic TUI, fresh fixed-expiry tickets, history retained; no arbitrary focus", flush=True)
    finally:
        if monitor:
            monitor.stop()
        if tray:
            tray.destroy()
        if history:
            history.close()
        if (directory / "fixture.pid").exists():
            os.kill(pid, signal.SIGTERM)
        subprocess.run(["wmctrl", "-i", "-a", original_focus], check=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture_directory", type=Path)
    run(parser.parse_args().fixture_directory)
