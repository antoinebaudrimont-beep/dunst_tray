#!/usr/bin/env python3
"""Capture real GTK/Xfce pixels with fictional data on an isolated X11/bus.

Requires opt-in Xvfb, xauth, Xfce panel/WM, xterm, feh, Dunst and xdotool. Pass the
existing offline Go fixture built with WALITE_TRAY_SCREENSHOT_DATA support.
No normal tray/app is stopped; no host D-Bus calls or notification data are read.
The isolated display is cookie-protected and has no TCP listener. Output PNGs
are direct framebuffer captures (optional bounds crop), lossless compression 9.
There is no image compositing, UI mockup, retouching or application-code patch.
"""
from __future__ import annotations

import argparse
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=4)


def isolated(arguments):
    binary = arguments.xvfb or shutil.which("Xvfb")
    if not binary:
        raise RuntimeError("Pass --xvfb with an available Xvfb executable")
    with tempfile.TemporaryDirectory(prefix="dunst-screenshot-session-") as temporary:
        root = Path(temporary)
        for name in ("config", "data", "cache", "runtime", "walite", "logs"):
            (root / name).mkdir(mode=0o700)
        channel = root / "config/xfce4/xfconf/xfce-perchannel-xml"
        channel.mkdir(parents=True)
        shutil.copyfile(REPO / "tests/fixtures/screenshots-panel.xml",
                        channel / "xfce4-panel.xml")
        for number in range(90, 200):
            if not Path(f"/tmp/.X11-unix/X{number}").exists() and not Path(f"/tmp/.X{number}-lock").exists():
                display = f":{number}"
                break
        else:
            raise RuntimeError("No unused isolated X11 display")
        authority = root / "Xauthority"
        authority.touch(mode=0o600)
        subprocess.run(["xauth", "-f", str(authority), "add", display, ".",
                        secrets.token_hex(16)], check=True, capture_output=True)
        environment = {
            **os.environ, "DISPLAY": display, "XAUTHORITY": str(authority),
            "XDG_CONFIG_HOME": str(root / "config"),
            "XDG_DATA_HOME": str(root / "data"),
            "XDG_CACHE_HOME": str(root / "cache"),
            "XDG_RUNTIME_DIR": str(root / "runtime"),
            "GTK_THEME": arguments.theme, "LC_ALL": "C.UTF-8",
            "DUNST_SCREENSHOT_HOST_BUS": os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""),
            "DUNST_SCREENSHOT_HOST_DISPLAY": os.environ.get("DISPLAY", ""),
            "PYTHONPATH": str(REPO / "src"),
        }
        with (root / "logs/xserver.log").open("w") as log:
            server = subprocess.Popen([
                str(binary), display, "-screen", "0", "1120x960x24",
                "-nolisten", "tcp", "-auth", str(authority),
            ], stdout=log, stderr=log, start_new_session=True)
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if server.poll() is not None:
                        raise RuntimeError("Isolated X server failed")
                    if subprocess.run(["xdpyinfo"], env=environment,
                                      capture_output=True).returncode == 0:
                        break
                    time.sleep(.05)
                else:
                    raise RuntimeError("Isolated X server did not become ready")
                subprocess.run([
                    "dbus-run-session", "--", sys.executable, str(Path(__file__).resolve()),
                    "--session", str(root), "--walite-fixture", str(arguments.walite_fixture.resolve()),
                    "--output", str(arguments.output.resolve()),
                    "--theme", arguments.theme, "--font", arguments.font,
                ], env=environment, check=True, timeout=180)
            finally:
                stop(server)


def capture_session(arguments):
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GdkX11", "3.0")
    from gi.repository import Gdk, GdkPixbuf, GdkX11, Gio, GLib, Gtk
    from dunst_tray.capture import NotificationMonitor
    from dunst_tray.config import AppConfig, save_appearance, load_config
    from dunst_tray.dunst import DunstController
    from dunst_tray.history import HistoryStore
    from dunst_tray.ui import TrayApplication

    Gtk.Settings.get_default().set_property("gtk-font-name", arguments.font)

    root = arguments.session.resolve()
    assert root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o777 == 0o700
    assert os.environ["DBUS_SESSION_BUS_ADDRESS"] != os.environ["DUNST_SCREENSHOT_HOST_BUS"]
    assert os.environ["DISPLAY"] != os.environ["DUNST_SCREENSHOT_HOST_DISPLAY"]
    for variable, suffix in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"),
                             ("XDG_CACHE_HOME", "cache"), ("XDG_RUNTIME_DIR", "runtime")):
        assert Path(os.environ[variable]).resolve() == root / suffix
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    children, windows = [], []
    history = tray = monitor = None
    fixture_pid = None

    def start(name, command, environment=None):
        with (root / "logs" / f"{name}.log").open("w") as log:
            child = subprocess.Popen(command, env=environment, stdout=log, stderr=log,
                                     start_new_session=True)
        children.append(child)
        return child

    def spin(predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            if predicate():
                return
            time.sleep(.01)
        raise AssertionError("Screenshot condition did not become ready")

    def wait(seconds):
        deadline = time.monotonic() + seconds
        spin(lambda: time.monotonic() >= deadline, seconds + 1)

    def click(widget):
        spin(widget.get_mapped)
        wait(.15)
        top = widget.get_toplevel()
        x, y = widget.translate_coordinates(top, 0, 0)
        allocation = widget.get_allocation()
        subprocess.run([
            "xdotool", "mousemove", "--window", str(top.get_window().get_xid()),
            str(x + allocation.width // 2), str(y + allocation.height // 2),
            "click", "1",
        ], check=True)
        wait(.15)

    def snap(filename, window=None):
        subprocess.run(["xdotool", "mousemove", "0", "950"], check=True)
        wait(.35)
        screen = Gdk.get_default_root_window()
        if window:
            rectangle = window.get_window().get_frame_extents()
            x, y = max(0, rectangle.x - 18), max(0, rectangle.y - 18)
            width = min(1120 - x, rectangle.width + 36)
            height = min(960 - y, rectangle.height + 36)
        else:
            x, y, width, height = 0, 0, 1120, 960
        pixbuf = Gdk.pixbuf_get_from_window(screen, x, y, width, height)
        assert pixbuf is not None
        pixbuf.savev(str(output / filename), "png", ["compression"], ["9"])
        decoded = GdkPixbuf.Pixbuf.new_from_file(str(output / filename))
        assert decoded.get_pixels() == pixbuf.get_pixels()
        print(f"CAPTURE {filename}: {width}x{height}, lossless framebuffer pixels", flush=True)

    try:
        start("wm", ["xfwm4", "--compositor=on"])
        start("panel", ["xfce4-panel", "--disable-wm-check"])
        start("dunst", ["dunst", "-config", str(REPO / "tests/fixtures/screenshots-dunst.conf")])
        wait(1)
        background = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 1120, 960)
        background.fill(0x152231ff)
        background.savev(str(root / "background.png"), "png", [], [])
        # --no-fehbg prevents writing the normal user's ~/.fehbg.
        subprocess.run(["feh", "--no-fehbg", "--bg-fill", str(root / "background.png")], check=True)
        fixture_environment = {
            **os.environ, "WALITE_TRAY_TEST_DIR": str(root / "walite"),
            "WALITE_TRAY_SCREENSHOT_DATA": "1", "TERM": "xterm-256color",
        }
        start("walite", ["xterm", "-title", "Offline fictional Walite fixture",
                          "-e", str(arguments.walite_fixture),
                          "-test.run=^TestDunstTrayNavigationFixture$", "-test.timeout=5m"],
              fixture_environment)
        spin(lambda: (root / "walite/fixture.pid").exists()
             and (root / "walite/screen.state").exists())
        fixture_pid = int((root / "walite/fixture.pid").read_text())
        fixture_window = (root / "walite/fixture.window").read_text()
        config_path = root / "config/dunst-tray/config.ini"
        config = save_appearance(replace(AppConfig(), panel_width=440, panel_height=850,
                                         margin_top=66, margin_right=32), config_path)
        history = HistoryStore(root / "data/dunst-tray/history.sqlite3")
        tray = TrayApplication(config, config_path, history, DunstController(), Gtk.main_quit)
        monitor = NotificationMonitor(history, tray.notification_received)
        monitor.start()
        spin(tray.status_icon.is_embedded)
        spin(lambda: tray.window.get_screen().is_composited())
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        def send(app, title, body, icon, desktop):
            count = history.count()
            bus.call_sync(
                "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications", "Notify",
                GLib.Variant("(susssasa{sv}i)", (
                    app, 0, icon, title, body, [],
                    {"transient": GLib.Variant("b", True),
                     "desktop-entry": GLib.Variant("s", desktop)}, 500,
                )), None, Gio.DBusCallFlags.NONE, 3000, None,
            )
            spin(lambda: history.count() == count + 1)

        for app, title, body, icon, identity in (
            ("Web Browser", "Download complete", "The illustrated trail guide is ready.",
             "web-browser", "demo-browser"),
            ("Calendar", "Studio workshop", "Tomorrow at 10:00 — Sketch Studio.",
             "x-office-calendar", "demo-calendar"),
        ):
            window = Gtk.Window(title="Fictional application fixture")
            window.set_wmclass(identity, identity)
            window.show_all()
            window.iconify()
            windows.append(window)
            # Installed test desktop metadata only, not a resolver override.
            directory = root / "data/applications"
            directory.mkdir(exist_ok=True)
            (directory / f"{identity}.desktop").write_text(
                f"[Desktop Entry]\nType=Application\nName={app}\n"
                f"StartupWMClass={identity}\nIcon={icon}\n",
            )
            send(app, title, body, icon, identity)
        # Refresh catalog after installing isolated fictional desktop entries.
        from dunst_tray.applications import ApplicationCatalog
        tray.applications = ApplicationCatalog()
        tray.desktop.catalog = tray.applications

        def walite(group=False):
            count = history.count()
            os.kill(fixture_pid, signal.SIGUSR2 if group else signal.SIGUSR1)
            spin(lambda: history.count() == count + 1)
            assert history.latest().walite_activation is not None
            return history.latest()

        def expanded():
            if not tray.window.get_visible():
                tray.toggle_center()
            wait(.2)
            card = next(card for card in tray.groups_box.get_children()
                        if card.notifications[0].app_name == "walite")
            if not card.expanded:
                click(card.header)
            return card

        def navigation(item, state):
            tray.dunst._run("close-all")
            wait(.3)
            previous = history.latest().walite_activation
            card = expanded()
            controls = card.messages.get_children()[0].get_children()[-1].get_children()[-1]
            control = next(child for child in controls.get_children()
                           if isinstance(child, Gtk.Button) and child.get_label() == "Open discussion")
            assert control.get_sensitive()
            click(control)
            spin(lambda: not tray.window.get_visible()
                 and (root / "walite/screen.state").read_text() == state)
            assert history.latest().walite_activation != previous

        navigation(walite(True), "GROUP")
        for _ in range(6):
            walite()
        navigation(history.latest(), "DIRECT")
        subprocess.run(["xdotool", "windowminimize", fixture_window], check=True)
        tray.dunst._run("close-all")  # Only this isolated bus, all synthetic.
        card = expanded()
        assert len(card.notifications) == 7 and card.visible_count == 5
        assert len(tray.groups_box.get_children()) == 3
        wait(.5)
        snap("notification-center.png", tray.window)

        tray.window.hide()
        tray._show_settings(None)
        dialog = tray.settings_dialog
        dialog.auto_hide.set_active(True)
        dialog.auto_hide_timeout.set_value(5)
        click(dialog.get_widget_for_response(Gtk.ResponseType.APPLY))
        assert load_config(config_path).auto_hide_timeout == 5 and tray.config.auto_hide
        assert tray.auto_hide.source is None  # Settings protects the center.
        dialog.present()
        wait(.3)
        snap("settings.png", dialog)
        click(dialog.get_widget_for_response(Gtk.ResponseType.CANCEL))
        spin(lambda: tray.settings_dialog is None)

        expanded()
        send("Calendar", "Sketch Studio reminder", "Bring your favorite colored pencils.",
             "x-office-calendar", "demo-calendar")
        tray.dunst._run("close-all")
        spin(lambda: tray.unread == 1)
        assert tray.status_icon.is_embedded() and tray.window.get_visible()
        assert history.count() == 10
        snap("desktop-integration.png")
        print("PASS real v2 discussion actions, three groups, five displayed messages, older navigation", flush=True)
        print("PASS Settings applied auto-hide at five seconds; unread arrived after opening", flush=True)
    finally:
        if monitor:
            monitor.stop()
        if tray:
            tray.destroy()
        if history:
            history.close()
        for window in windows:
            window.destroy()
        if fixture_pid and (root / "walite/fixture.pid").exists():
            os.kill(fixture_pid, signal.SIGTERM)
        for child in reversed(children):
            stop(child)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xvfb", type=Path)
    parser.add_argument("--walite-fixture", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=REPO / "docs/screenshots")
    parser.add_argument("--session", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--theme", default="Greybird-dark")
    parser.add_argument("--font", default="Sans 10")
    options = parser.parse_args()
    if options.session:
        capture_session(options)
    else:
        isolated(options)
