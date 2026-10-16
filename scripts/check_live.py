#!/usr/bin/env python3
"""Opt-in X11 acceptance with synthetic data; briefly changes/restores DND.

Stop the normal tray first so it cannot retain fixtures, then run:
    PYTHONPATH=src python3 scripts/check_live.py
Restart the normal tray afterward. No Dunst configuration is changed. The
script filters out real notification content, uses a temporary SQLite store,
never launches target applications, and never clears the user's Dunst history.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gio, GLib, Gtk, GdkX11  # noqa: E402,F401

from dunst_tray.capture import NotificationMonitor
from dunst_tray.config import AppConfig, load_config
from dunst_tray.dunst import DunstController
from dunst_tray.history import HistoryStore
from dunst_tray.ui import TrayApplication

PREFIX = "DunstTraySyntheticAcceptance:"


def command(*arguments):
    return subprocess.check_output(arguments, text=True).strip()


def spin(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for an acceptance condition")


def active_window():
    return re.search(r"0x[0-9a-f]+", command(
        "xprop", "-root", "_NET_ACTIVE_WINDOW"
    )).group()


class SyntheticHistory(HistoryStore):
    def add(self, notification):
        if not notification.summary.startswith(PREFIX):
            return -1
        return super().add(notification)


class ProtectedDunst(DunstController):
    """Real pause controls, but an explicit NO-OP for daemon history clearing."""
    def __init__(self):
        super().__init__()
        self.synthetic_ids = set()

    def clear_history(self):
        # Exercise only the companion's temporary SQLite clear in this script.
        # Never invoke Dunst history-clear or history-rm on the user's session.
        pass


def run():
    controller = ProtectedDunst()
    original_pause_level = controller._run("get-pause-level")
    original_focus = active_window()
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def owner():
        return bus.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "GetNameOwner",
            GLib.Variant("(s)", ("org.freedesktop.Notifications",)), None,
            Gio.DBusCallFlags.NONE, 3000, None,
        ).unpack()[0]

    original_owner = owner()
    tray = monitor = history = None
    temporary = tempfile.TemporaryDirectory(prefix="dunst-tray-acceptance-")
    folder = Path(temporary.name)
    sequence = 0

    def send(app="Synthetic future app", desktop=""):
        nonlocal sequence
        sequence += 1
        hints = {"desktop-entry": GLib.Variant("s", desktop)} if desktop else {}
        # Transient hints prevent test entries remaining in Dunst history.
        hints["transient"] = GLib.Variant("b", True)
        result = bus.call_sync(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications", "Notify",
            GLib.Variant("(susssasa{sv}i)", (
                app, 0, "", f"{PREFIX}{sequence}", "Synthetic test body",
                ["default", "Open"], hints, 150,
            )), None, Gio.DBusCallFlags.NONE, 3000, None,
        ).unpack()[0]
        controller.synthetic_ids.add(result)

    def click_widget(widget):
        top = widget.get_toplevel()
        spin(lambda: widget.get_mapped())
        widget.grab_focus()
        # Allow a frame for final allocation before computing mouse position.
        for _ in range(8):
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.01)
        point = widget.translate_coordinates(top, 0, 0)
        allocation = widget.get_allocation()
        command("xdotool", "mousemove", "--window",
                str(top.get_window().get_xid()),
                str(point[0] + allocation.width // 2),
                str(point[1] + allocation.height // 2), "click", "1")

    def click_bell():
        command("xdotool", "mousemove", "--window",
                str(tray.status_icon.get_x11_window_id()), "8", "8", "click", "1")

    try:
        history = SyntheticHistory(folder / "history.sqlite3")
        tray = TrayApplication(AppConfig(), folder / "config.ini", history,
                               controller, lambda: None)
        monitor = NotificationMonitor(history, tray.notification_received)
        monitor.start()
        spin(lambda: tray.status_icon.is_embedded())
        clean = tray.status_icon.get_pixbuf().get_pixels()
        assert tray.unread == 0
        print("PASS actual Xfce XEmbed clean bell", flush=True)

        send()
        spin(lambda: tray.unread == 1)
        dotted = tray.status_icon.get_pixbuf().get_pixels()
        assert clean != dotted
        click_bell()
        spin(lambda: tray.window.get_visible() and tray.unread == 0)
        send()
        spin(lambda: tray.unread == 1)
        click_bell()
        spin(lambda: not tray.window.get_visible())
        assert tray.unread == 1
        click_bell()
        spin(lambda: tray.window.get_visible() and tray.unread == 0)
        click_bell()
        spin(lambda: not tray.window.get_visible())
        print("PASS one dot, physical bell toggle, review and arrivals while open",
              flush=True)

        controller._run("set-pause-level", "1")
        tray.refresh_dunst_state()
        for _ in range(20):
            send("walite")
        spin(lambda: tray.unread == 20)
        assert tray.status_icon.get_pixbuf().get_pixels() == dotted
        assert history.count() == 22
        print("PASS twenty captured Walite calls, one dot, real DND", flush=True)

        monitor.stop()
        tray.destroy()
        history.close()
        history = SyntheticHistory(folder / "history.sqlite3")
        tray = TrayApplication(load_config(folder / "config.ini"),
                               folder / "config.ini", history, controller,
                               lambda: None)
        monitor = NotificationMonitor(history, tray.notification_received)
        monitor.start()
        spin(lambda: tray.status_icon.is_embedded())
        assert tray.unread == 20
        print("PASS unread restoration after tray reconstruction", flush=True)

        tray._show_settings(None)
        dialog = tray.settings_dialog
        dialog.width.set_value(320)
        dialog.height.set_value(430)
        dialog.opacity.set_value(70)
        dialog.radius.set_value(20)
        dialog.show_icons.set_active(False)
        click_widget(dialog.get_widget_for_response(Gtk.ResponseType.APPLY))
        spin(lambda: tray.config.panel_width == 320)
        assert load_config(folder / "config.ini") == tray.config
        assert history.unread_count() == 20
        click_widget(dialog.get_widget_for_response(Gtk.ResponseType.CANCEL))
        spin(lambda: tray.settings_dialog is None)
        assert tray.status_icon.get_visible()
        print("PASS physical settings Apply/Cancel and saved appearance", flush=True)

        controller._run("set-pause-level", original_pause_level)
        # These notifications identify already-running apps. This verifies
        # focus only; no native callback or exact-message navigation is claimed.
        for app, desktop in (("ChatGPT", "chatgpt"),
                             ("Task Manager", "xfce4-taskmanager"),
                             ("walite", "")):
            send(app, desktop)
            spin(lambda: any(item.app_name == app for item in history.all()))
            item = next(item for item in history.all() if item.app_name == app)
            expected = (tray.walite.find_window() if app == "walite"
                        else tray.desktop.find_window(item))
            if not tray.window.get_visible():
                click_bell()
                spin(lambda: tray.window.get_visible())
            tray.refresh()
            card = next(card for card in tray.groups_box.get_children()
                        if card.notifications[0].app_name == app)
            if not card.expanded:
                card._toggle(None)
            button = card.messages.get_children()[0].get_children()[-1]
            button = button.get_children()[-1]
            button = next(child for child in button.get_children()
                          if isinstance(child, Gtk.Button)
                          and child.get_label() == "Show app")
            spin(lambda: button.get_mapped())
            assert button.get_sensitive()
            click_widget(button)
            spin(lambda: int(active_window(), 16) == int(expected, 16))
            assert not tray.window.get_visible()
            print(f"PASS physical Show app focus: {app}", flush=True)

        def confirm_clear():
            for window in Gtk.Window.list_toplevels():
                if isinstance(window, Gtk.MessageDialog):
                    window.response(Gtk.ResponseType.OK)
            return False

        GLib.timeout_add(100, confirm_clear)
        tray._confirm_clear(None)
        assert history.count() == 0 and tray.unread == 0
        assert tray.status_icon.get_visible()
        assert owner() == original_owner
        print("PASS local clear, persistent bell, unchanged Dunst service owner",
              flush=True)
        monitor.stop()
        tray.destroy()
        history.close()
        history = SyntheticHistory(folder / "history.sqlite3")
        tray = TrayApplication(load_config(folder / "config.ini"),
                               folder / "config.ini", history, controller,
                               lambda: None)
        spin(lambda: tray.status_icon.is_embedded())
        assert tray.config.panel_width == 320
        assert tray.config.panel_opacity == 70
        assert not tray.config.show_icons
        assert tray.unread == 0
        print("PASS appearance and clean unread state after restart", flush=True)
    finally:
        if monitor:
            monitor.stop()
        if tray:
            tray.destroy()
        if history:
            history.close()
        controller._run("set-pause-level", original_pause_level)
        # Each ID came directly from this script's own Notify call. The
        # transient hint prevents these synthetic notices entering history.
        # CloseNotification affects only that ID, never daemon history.
        for notification_id in controller.synthetic_ids:
            try:
                bus.call_sync(
                    "org.freedesktop.Notifications",
                    "/org/freedesktop/Notifications",
                    "org.freedesktop.Notifications", "CloseNotification",
                    GLib.Variant("(u)", (notification_id,)), None,
                    Gio.DBusCallFlags.NONE, 3000, None,
                )
            except GLib.Error:
                pass  # It may already have expired.
        subprocess.run(["wmctrl", "-i", "-a", original_focus], check=False)
        temporary.cleanup()


if __name__ == "__main__":
    run()
