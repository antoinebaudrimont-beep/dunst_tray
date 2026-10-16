#!/usr/bin/env python3
"""Opt-in X11 checks: stop ONLY the normal tray first; restart it afterward.

Uses transient synthetic notifications, a filtered temporary history/config,
and the real GTK event loop/mouse. Never reads private message content, sends
messages, changes DND, or clears daemon history. Targets already-running apps;
only disposable synthetic GTK/terminal windows are created and closed here.
Requires xdotool and kitty for acceptance, not for normal application use.
"""
from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gio, GLib, Gtk, GdkX11  # noqa: E402,F401

from check_live import (  # noqa: E402
    PREFIX, ProtectedDunst, SyntheticHistory, active_window, command, spin,
)
from check_walite_live import click  # noqa: E402
from dunst_tray.activation import ActivationError  # noqa: E402
from dunst_tray.applications import DesktopApplication  # noqa: E402
from dunst_tray.capture import NotificationMonitor  # noqa: E402
from dunst_tray.config import AppConfig, load_config  # noqa: E402
from dunst_tray.ui import TrayApplication  # noqa: E402


def wait(seconds):
    deadline = time.monotonic() + seconds
    spin(lambda: time.monotonic() >= deadline, timeout=seconds + 1)


def run():
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    original_focus = active_window()
    controller = ProtectedDunst()
    original_pause = controller._run("get-pause-level")
    def owner():
        return bus.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus",
            "org.freedesktop.DBus", "GetNameOwner",
            GLib.Variant("(s)", ("org.freedesktop.Notifications",)), None,
            Gio.DBusCallFlags.NONE, 3000, None,
        ).unpack()[0]

    original_owner = owner()
    fixture_windows = []
    terminal_windows = []
    tray = monitor = history = None
    sequence = 0

    def send(app, desktop=""):
        nonlocal sequence
        sequence += 1
        hints = {"transient": GLib.Variant("b", True)}
        if desktop:
            hints["desktop-entry"] = GLib.Variant("s", desktop)
        result = bus.call_sync(
            "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
            "org.freedesktop.Notifications", "Notify",
            GLib.Variant("(susssasa{sv}i)", (
                app, 0, "missing-synthetic-icon", f"{PREFIX}{sequence}",
                "Synthetic body: no email or WhatsApp data", [], hints, 150,
            )), None, Gio.DBusCallFlags.NONE, 3000, None,
        ).unpack()[0]
        controller.synthetic_ids.add(result)
        spin(lambda: history.count() == sequence)
        return history.latest()

    def open_center():
        if not tray.window.get_visible():
            tray.toggle_center()
        wait(0.15)

    def button(item):
        open_center()
        tray.refresh()
        wait(0.15)
        card = next(card for card in tray.groups_box.get_children()
                    if card.notifications[0].app_name == item.app_name)
        if not card.expanded:
            click(card.header)
            wait(0.15)
        message = card.messages.get_children()[0]
        controls = message.get_children()[-1].get_children()[-1]
        return next(child for child in controls.get_children()
                    if isinstance(child, Gtk.Button)
                    and child.get_label() == "Show app")

    def fixture(name):
        window = Gtk.Window(title="Synthetic acceptance window")
        window.set_wmclass(name, name)
        window.set_default_size(250, 120)
        window.show_all()
        fixture_windows.append(window)
        wait(0.2)
        return window

    def terminal_ids():
        # Fixture discovery only; production never uses titles for matching.
        return {window for window in tray.desktop._window_ids()
                if '"DunstTrayTerminalFixture"' in tray.desktop._run(
                    "xprop", "-id", window, "WM_CLASS")}

    try:
        with tempfile.TemporaryDirectory(prefix="dunst-actions-autohide-") as temporary:
            folder = Path(temporary)
            history = SyntheticHistory(folder / "history.sqlite3")
            tray = TrayApplication(AppConfig(), folder / "config.ini", history,
                                   controller, lambda: None)
            monitor = NotificationMonitor(history, tray.notification_received)
            monitor.start()
            spin(lambda: tray.status_icon.is_embedded())
            for app, desktop in (("aerc", "aerc"), ("ChatGPT", "chatgpt"),
                                 ("Task Manager", "xfce4-taskmanager"),
                                 ("walite", "")):
                item = send(app, desktop)
                expected = (tray.walite.find_window() if app == "walite"
                            else tray.desktop.find_window(item))
                if app == "aerc":
                    command("xdotool", "windowminimize", expected)
                    wait(0.2)
                control = button(item)
                assert control.get_sensitive()
                click(control)
                spin(lambda: int(active_window(), 16) == int(expected, 16))
                assert not tray.window.get_visible()
                print(f"PASS physical no-action Show app: {app}", flush=True)

            window = fixture("DunstTraySyntheticGTK")
            item = send("DunstTraySyntheticGTK")
            expected = window.get_window().get_xid()
            click(button(item))
            spin(lambda: int(active_window(), 16) == expected)
            print("PASS ordinary GTK app; missing icon; exact app-name WM_CLASS", flush=True)

            item = send("DunstTrayUnknownIdentity")
            assert not button(item).get_sensitive()
            fixture("DunstTrayAmbiguous")
            fixture("DunstTrayAmbiguous")
            item = send("DunstTrayAmbiguous")
            assert not button(item).get_sensitive()
            tray.window.hide()
            print("PASS unknown and ambiguous windows disabled", flush=True)

            tray.applications.applications.append(DesktopApplication(
                "org.example.TerminalFixture", "Synthetic Terminal", "",
                frozenset({"no-matching-window-class"}), "sleep", True,
            ))
            before = terminal_ids()
            for count in range(2):
                subprocess.run([
                    "kitty", "--detach", "--class", "DunstTrayTerminalFixture",
                    "--", "/usr/bin/sleep", "120",
                ], check=True)
                spin(lambda: len(terminal_ids() - before) == count + 1)
                terminal_windows = sorted(terminal_ids() - before)
                item = send("Synthetic Terminal", "org.example.TerminalFixture")
                if count == 0:
                    expected = tray.desktop.find_window(item)
                    click(button(item))
                    spin(lambda: int(active_window(), 16) == int(expected, 16))
                else:
                    with_error = False
                    try:
                        tray.desktop.find_window(item)
                    except ActivationError:
                        with_error = True
                    assert with_error and not button(item).get_sensitive()
                    tray.window.hide()
            print("PASS foreground process/PTY focus and multiple-terminal rejection", flush=True)

            open_center()
            wait(3.3)
            assert tray.window.get_visible() and tray.auto_hide.source is None
            tray._show_settings(None)
            dialog = tray.settings_dialog
            dialog.auto_hide.set_active(True)
            dialog.auto_hide_timeout.set_value(3)
            click(dialog.get_widget_for_response(Gtk.ResponseType.APPLY))
            spin(lambda: load_config(folder / "config.ini").auto_hide)
            wait(3.3)
            assert tray.window.get_visible() and tray.auto_hide.source is None
            click(dialog.get_widget_for_response(Gtk.ResponseType.CANCEL))
            spin(lambda: tray.settings_dialog is None)
            print("PASS disabled stays open; physical Apply persists; Settings pauses", flush=True)

            # A new arrival while open stays unread even after automatic hiding.
            send("DunstTrayUnknownIdentity")
            count, unread = history.count(), history.unread_count()
            assert unread == 1
            command("xdotool", "mousemove", "0", "400")
            spin(lambda: not tray.window.get_visible(), timeout=4)
            assert history.count() == count and history.unread_count() == unread
            assert tray.status_icon.is_embedded()
            print("PASS real timeout hides only; history/unread/bell preserved", flush=True)

            open_center()
            assert history.unread_count() == 0
            wait(2)
            xid = str(tray.window.get_window().get_xid())
            command("xdotool", "mousemove", "--window", xid, "70", "20")
            wait(1.5)
            assert tray.window.get_visible()
            spin(lambda: not tray.window.get_visible(), timeout=2.5)
            print("PASS physical mouse motion resets timeout", flush=True)

            open_center()
            wait(2)
            command("xdotool", "mousemove", "--window", xid, "100", "100", "click", "5")
            wait(1.5)
            assert tray.window.get_visible()
            spin(lambda: not tray.window.get_visible(), timeout=2.5)
            print("PASS physical scroll resets timeout", flush=True)

            open_center()
            control = tray.groups_box.get_children()[0].header
            x, y = control.translate_coordinates(tray.window, 0, 0)
            allocation = control.get_allocation()
            command("xdotool", "mousemove", "--window", xid,
                    str(x + allocation.width // 2),
                    str(y + allocation.height // 2), "mousedown", "1")
            wait(3.3)
            assert tray.window.get_visible() and tray.auto_hide.source is None
            command("xdotool", "mouseup", "1")
            spin(lambda: not tray.window.get_visible(), timeout=4)
            print("PASS held mouse control pauses timeout", flush=True)

            for _ in range(15):
                tray.toggle_center()
                assert tray.auto_hide.source is not None
                tray.toggle_center()
                assert tray.auto_hide.source is None
            monitor.stop()
            monitor = None
            saved = load_config(folder / "config.ini")
            tray.destroy()
            tray = TrayApplication(saved, folder / "config.ini", history,
                                   controller, lambda: None)
            spin(lambda: tray.status_icon.is_embedded())
            assert tray.config.auto_hide and tray.config.auto_hide_timeout == 3
            assert history.count() == count and history.unread_count() == 0
            assert controller._run("get-pause-level") == original_pause
            assert owner() == original_owner
            print("PASS repeated reopen/cancel; preference restart; unchanged DND", flush=True)
    finally:
        command("xdotool", "mouseup", "1")
        if monitor:
            monitor.stop()
        if tray:
            tray.destroy()
        if history:
            history.close()
        for window in fixture_windows:
            window.destroy()
        for window in terminal_windows:
            subprocess.run(["wmctrl", "-i", "-c", window], check=False)
        for notification_id in controller.synthetic_ids:
            try:
                bus.call_sync(
                    "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                    "org.freedesktop.Notifications", "CloseNotification",
                    GLib.Variant("(u)", (notification_id,)), None,
                    Gio.DBusCallFlags.NONE, 3000, None,
                )
            except GLib.Error:
                pass
        subprocess.run(["wmctrl", "-i", "-a", original_focus], check=False)


if __name__ == "__main__":
    run()
