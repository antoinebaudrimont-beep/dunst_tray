"""Opt-in GTK checks: DUNST_TRAY_GUI_TESTS=1; no real notification data."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path

from dunst_tray.applications import ApplicationCatalog, DesktopApplication
from test_activation import notification

GUI = os.environ.get("DUNST_TRAY_GUI_TESTS") == "1"


@unittest.skipUnless(GUI, "opt-in GTK/X11 checks")
class IconTests(unittest.TestCase):
    def setUp(self):
        from dunst_tray.ui import GdkPixbuf, GroupCard, Gtk
        if not Gtk.init_check()[0]:
            self.skipTest("GTK display unavailable")
        self.Gtk, self.Pixbuf, self.GroupCard = Gtk, GdkPixbuf.Pixbuf, GroupCard
        self.catalog = ApplicationCatalog([])

    def image(self, item):
        return self.GroupCard._application_icon(item, self.catalog)

    def test_theme_icon_and_missing_icon_fallback(self):
        image = self.image(replace(notification(), app_icon="utilities-terminal"))
        self.assertEqual(image.get_icon_name()[0], "utilities-terminal")
        missing = self.image(notification("Unknown future app"))
        self.assertEqual(missing.get_icon_name()[0], "dialog-information-symbolic")

    def test_absolute_png_and_stale_path_desktop_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            png = str(Path(directory) / "synthetic.png")
            from dunst_tray.ui import GdkPixbuf
            pixbuf = self.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 32, 32)
            pixbuf.fill(0x3399FFFF)
            pixbuf.savev(png, "png", [], [])
            item = replace(notification("Synthetic"), app_icon=png)
            self.assertIsNotNone(self.image(item).get_pixbuf())
            self.catalog.applications.append(DesktopApplication(
                "synthetic", "Synthetic", "utilities-terminal",
                frozenset({"synthetic"}),
            ))
            Path(png).unlink()
            self.assertEqual(self.image(item).get_icon_name()[0],
                             "utilities-terminal")

    def test_synthetic_future_aerc_icon_uses_generic_desktop_metadata(self):
        self.catalog.applications.append(DesktopApplication(
            "aerc", "aerc", "utilities-terminal", frozenset({"aerc"}),
        ))
        image = self.image(replace(notification("aerc"), desktop_entry="aerc"))
        self.assertEqual(image.get_icon_name()[0], "utilities-terminal")

    def test_clean_bell_and_single_white_dot_at_panel_sizes(self):
        from dunst_tray.tray_icon import render_bell
        for size in (16, 22, 24, 32):
            for color in ((0.12, 0.12, 0.12), (0.95, 0.95, 0.95)):
                clean = render_bell(size, False, color)
                unread = render_bell(size, True, color)
                self.assertEqual(clean.get_width(), size)
                self.assertEqual(unread.get_height(), size)
                self.assertNotEqual(clean.get_pixels(), unread.get_pixels())
                x, y = round(size * 19.3 / 24), round(size * 4.7 / 24)
                offset = y * unread.get_rowstride() + x * 4
                self.assertEqual(unread.get_pixels()[offset:offset + 3],
                                 b"\xff\xff\xff")


class FakeDunst:
    def __init__(self):
        self.paused = False

    def is_paused(self):
        return self.paused

    def set_paused(self, paused):
        self.paused = paused

    def clear_history(self):
        pass


@unittest.skipUnless(GUI, "opt-in GTK/X11 checks")
class TrayStateTests(unittest.TestCase):
    def setUp(self):
        from dunst_tray.config import AppConfig
        from dunst_tray.history import HistoryStore
        from dunst_tray.ui import TrayApplication
        self.temporary = tempfile.TemporaryDirectory()
        self.folder = Path(self.temporary.name)
        self.history = HistoryStore(self.folder / "history.sqlite3")
        self.dunst = FakeDunst()
        with patch("dunst_tray.ui.ApplicationCatalog",
                   return_value=ApplicationCatalog([])):
            self.tray = TrayApplication(
                AppConfig(), self.folder / "config.ini", self.history,
                self.dunst, lambda: None,
            )

    def tearDown(self):
        self.tray.destroy()
        self.history.close()
        self.temporary.cleanup()

    def test_auto_hide_settings_apply_cancel_defaults_and_reload(self):
        from dunst_tray.config import AppConfig, load_config
        from dunst_tray.settings import RESTORE_DEFAULTS
        self.tray._show_settings(None)
        dialog = self.tray.settings_dialog
        self.assertFalse(dialog.auto_hide.get_active())
        self.assertFalse(dialog.auto_hide_timeout.get_sensitive())
        dialog.auto_hide.set_active(True)
        dialog.auto_hide_timeout.set_value(9)
        dialog.response(self.GtkResponse("APPLY"))
        self.assertTrue(self.tray.config.auto_hide)
        self.assertEqual(load_config(self.tray.config_path).auto_hide_timeout, 9)
        dialog.auto_hide_timeout.set_value(20)
        dialog.response(self.GtkResponse("CANCEL"))
        self.assertEqual(self.tray.config.auto_hide_timeout, 9)
        self.tray._show_settings(None)
        self.tray.settings_dialog.response(RESTORE_DEFAULTS)
        self.assertFalse(self.tray.settings_dialog.auto_hide.get_active())
        self.assertEqual(self.tray.settings_dialog.auto_hide_timeout.get_value_as_int(), 5)
        self.tray.settings_dialog.response(self.GtkResponse("APPLY"))
        self.assertEqual(self.tray.config, AppConfig())

    @staticmethod
    def GtkResponse(name):
        from dunst_tray.ui import Gtk
        return getattr(Gtk.ResponseType, name)

    def test_auto_hide_activity_settings_hold_and_history_invariants(self):
        from dunst_tray.ui import Gdk, Gtk
        self.history.add(notification("Synthetic"))
        self.tray._apply_appearance(replace(self.tray.config, auto_hide=True,
                                           auto_hide_timeout=3))
        now = [0.0]
        self.tray.auto_hide.clock = lambda: now[0]
        self.tray.toggle_center()
        self.assertEqual(self.history.unread_count(), 0)
        self.history.add(replace(notification("Synthetic"), received_at=2))
        self.tray.notification_received()
        now[0] = 2
        for kind in (Gdk.EventType.MOTION_NOTIFY, Gdk.EventType.SCROLL,
                     Gdk.EventType.KEY_PRESS):
            self.tray._center_activity(self.tray.window, Gdk.Event.new(kind))
            self.assertEqual(self.tray.auto_hide.deadline, 5)
        self.tray._show_settings(None)
        self.assertIsNone(self.tray.auto_hide.source)
        now[0] = 30
        self.tray.auto_hide._expired()
        self.assertTrue(self.tray.window.get_visible())
        self.tray.settings_dialog.response(Gtk.ResponseType.CANCEL)
        self.assertIsNotNone(self.tray.auto_hide.source)
        # Cancel the actual source before manually delivering its fake deadline.
        self.tray.auto_hide._cancel()
        now[0] = 33
        self.tray.auto_hide._expired()
        self.assertFalse(self.tray.window.get_visible())
        self.assertEqual(self.history.count(), 2)
        self.assertEqual(self.history.unread_count(), 1)
        self.assertFalse(self.dunst.paused)
        self.assertTrue(self.tray.status_icon.get_visible())
        self.tray.toggle_center()
        self.assertEqual(self.history.unread_count(), 0)

    def test_no_action_record_still_has_show_app_and_unknown_is_explained(self):
        from dunst_tray.ui import GroupCard
        item = replace(notification("Unknown app"), actions=())
        card = GroupCard("Unknown app", [item], 5,
                         lambda _item: (False, "No unique identity"),
                         lambda _item: None, ApplicationCatalog([]))
        controls = card.messages.get_children()[0].get_children()[-1].get_children()[-1]
        show = controls.get_children()[0]
        self.assertEqual(show.get_label(), "Show app")
        self.assertFalse(show.get_sensitive())
        self.assertIn("No unique identity", show.get_tooltip_text())
        card.destroy()

    def test_modal_transaction_holds_timer_and_dynamic_child_events_reset_it(self):
        from dunst_tray.ui import Gdk, GLib, Gtk
        self.tray._apply_appearance(replace(self.tray.config, auto_hide=True))
        self.tray.toggle_center()
        child = Gtk.Button(label="Synthetic dynamic control")
        self.tray.groups_box.add(child)
        child.show()
        self.assertIn(child, self.tray._activity_widgets)
        now = [10.0]
        self.tray.auto_hide.clock = lambda: now[0]
        child.emit("event", Gdk.Event.new(Gdk.EventType.KEY_PRESS))
        self.assertEqual(self.tray.auto_hide.deadline, 15)
        for index in range(7):
            self.history.add(replace(notification("Synthetic"), received_at=index + 1))
        self.tray.refresh()
        self.assertNotIn(child, self.tray._activity_widgets)
        card = self.tray.groups_box.get_children()[0]
        control = card.messages.get_children()[0].get_children()[-1].get_children()[-1].get_children()[0]
        self.assertIn(control, self.tray._activity_widgets)
        card._show_older(None)
        self.assertNotIn(control, self.tray._activity_widgets)
        older_control = card.messages.get_children()[6].get_children()[-1].get_children()[-1].get_children()[0]
        self.assertIn(older_control, self.tray._activity_widgets)
        observed = []

        def close_modal():
            observed.append(self.tray.auto_hide.source is None)
            for window in Gtk.Window.list_toplevels():
                if isinstance(window, Gtk.MessageDialog):
                    window.response(Gtk.ResponseType.CANCEL)
            return False

        GLib.timeout_add(10, close_modal)
        self.tray._confirm_clear(None)
        self.assertEqual(observed, [True])
        self.assertIsNotNone(self.tray.auto_hide.source)

    def test_arrivals_review_dnd_and_window_lifecycle(self):
        self.history.add(notification("Synthetic App"))
        self.tray.notification_received()
        self.assertEqual(self.tray.unread, 1)
        dotted = self.tray.status_icon.get_pixbuf().get_pixels()
        self.dunst.paused = True
        self.tray.refresh_dunst_state()
        self.assertEqual(self.tray.status_icon.get_pixbuf().get_pixels(), dotted)
        self.assertEqual(self.tray.unread, 1)
        self.tray.toggle_center()
        self.assertEqual(self.history.unread_count(), 0)
        # Arrivals while open remain unread until a subsequent explicit review.
        self.history.add(notification("Synthetic App"))
        self.tray.notification_received()
        self.assertEqual(self.tray.unread, 1)
        self.tray.toggle_center()
        self.assertEqual(self.tray.unread, 1)
        self.tray.toggle_center()
        self.assertEqual(self.tray.unread, 0)
        self.tray._hide_window()
        self.assertTrue(self.tray.status_icon.get_visible())
        self.assertFalse(self.tray.window.get_visible())

    def test_settings_apply_cancel_defaults_and_icon_spacing(self):
        from dunst_tray.config import AppConfig, load_config
        from dunst_tray.settings import RESTORE_DEFAULTS
        from dunst_tray.ui import Gtk
        self.history.add(notification("Synthetic App"))
        self.tray.refresh()
        self.tray._show_settings(None)
        dialog = self.tray.settings_dialog
        self.tray._show_settings(None)
        self.assertIs(self.tray.settings_dialog, dialog)
        dialog.opacity.set_value(65)
        dialog.width.set_value(320)
        dialog.height.set_value(430)
        dialog.radius.set_value(24)
        dialog.show_icons.set_active(False)
        dialog.response(Gtk.ResponseType.APPLY)
        self.assertIn("Saved", dialog.status.get_text())
        self.assertEqual(self.tray.config.panel_opacity, 65)
        self.assertEqual(self.tray.config.corner_radius, 24)
        self.assertEqual(load_config(self.tray.config_path), self.tray.config)
        self.assertEqual(self.history.count(), 1)
        card = self.tray.groups_box.get_children()[0]
        self.assertEqual(len(card.header.get_child().get_children()), 2)
        saved = self.tray.config
        dialog.response(RESTORE_DEFAULTS)
        self.assertEqual(dialog.draft().panel_opacity, AppConfig().panel_opacity)
        self.assertEqual(self.tray.config, saved)
        dialog.response(Gtk.ResponseType.CANCEL)
        self.assertIsNone(self.tray.settings_dialog)
        self.assertEqual(self.tray.config, saved)
        self.tray._show_settings(None)
        self.assertEqual(self.tray.settings_dialog.width.get_value_as_int(), 320)
        self.tray.settings_dialog.response(RESTORE_DEFAULTS)
        self.tray.settings_dialog.response(Gtk.ResponseType.APPLY)
        self.assertEqual(self.tray.config, AppConfig())

    def test_refresh_preserves_expansion_and_paging(self):
        for number in range(10):
            self.history.add(replace(notification("Synthetic App"),
                                     received_at=number))
        self.tray.refresh()
        card = self.tray.groups_box.get_children()[0]
        card._toggle(card.header)
        card._show_older(None)
        self.tray.refresh()
        card = self.tray.groups_box.get_children()[0]
        self.assertTrue(card.expanded)
        self.assertEqual(card.visible_count, 10)

    def test_discussion_socket_action_is_separate_private_and_one_shot(self):
        import json
        import socket
        import threading
        from dunst_tray.walite import parse_activation
        from test_walite import hint
        with tempfile.TemporaryDirectory(prefix="walite-activation-") as directory:
            endpoint = Path(directory) / "s-synthetic.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(1)
                listener.settimeout(1)
                endpoint.chmod(0o600)
                received = []

                def receive():
                    connection, _address = listener.accept()
                    with connection:
                        connection.settimeout(1)
                        data = bytearray()
                        while True:
                            block = connection.recv(4096)
                            if not block:
                                break
                            data.extend(block)
                        received.append(json.loads(bytes(data)))

                item = replace(
                    notification("walite"),
                    walite_activation=parse_activation(hint(str(endpoint))),
                )
                self.history.add(item)
                stored = self.history.latest()
                with patch.object(self.tray.actions, "activate") as generic, \
                        patch.object(self.tray.walite_navigation, "send") as navigate:
                    self.tray._perform_action(stored)
                    generic.assert_called_once_with(stored)
                    navigate.assert_not_called()
                    self.assertIsNotNone(self.history.latest().walite_activation)
                reader = threading.Thread(target=receive)
                reader.start()
                with patch.object(self.tray.walite, "find_window", return_value="0x123"), \
                        patch.object(self.tray.walite, "raise_window") as focus, \
                        patch.object(self.tray.actions, "availability",
                                     return_value=(True, "Show application only")):
                    self.tray.refresh()
                    card = self.tray.groups_box.get_children()[0]
                    buttons = [child for child in card.messages.get_children()[0]
                               .get_children()[-1].get_children()[-1].get_children()
                               if hasattr(child, "get_label")]
                    labels = [button.get_label() for button in buttons]
                    self.assertIn("Show app", labels)
                    self.assertIn("Open discussion", labels)
                    self.tray._apply_appearance(replace(
                        self.tray.config, panel_width=280,
                    ))
                    self.tray.toggle_center()
                    import time
                    from dunst_tray.ui import Gtk
                    for _ in range(20):
                        while Gtk.events_pending():
                            Gtk.main_iteration_do(False)
                        time.sleep(0.01)
                    self.assertEqual(self.tray.window.get_size()[0], 280)
                    self.tray._open_walite_discussion(stored)
                    self.tray._open_walite_discussion(stored)
                    focus.assert_called_once_with("0x123")
                reader.join(timeout=1)
                self.assertFalse(reader.is_alive())
                self.assertEqual(received, [{"version": 1, "activation_id": "a" * 64}])
                self.assertIsNone(self.history.latest().walite_activation)
                self.assertEqual(self.history.count(), 1)
                # The explicit opening acknowledged the retained snapshot.
                self.assertEqual(self.history.unread_count(), 0)

    def test_discussion_hint_works_without_a_live_default_action(self):
        from dunst_tray.ui import GroupCard
        from dunst_tray.walite import parse_activation
        from test_walite import hint
        item = replace(notification("walite"), actions=(),
                       walite_activation=parse_activation(hint()))
        card = GroupCard(
            "walite", [item], 5, lambda _item: (False, "No live action"),
            lambda _item: self.fail("must not invoke generic action"),
            ApplicationCatalog([]), navigate_callback=lambda _item: None,
            navigation_availability=lambda _hint: (True, "Private request"),
        )
        footer = card.messages.get_children()[0].get_children()[-1]
        labels = [child.get_label() for child in
                  footer.get_children()[-1].get_children()]
        self.assertCountEqual(labels, ["Show app", "Open discussion"])
        card.destroy()

    def test_v2_successive_clicks_preserve_controls_and_independent_conversations(self):
        import time
        from dunst_tray.walite import parse_activation, WaliteActivationResult
        from test_walite import hint
        for index, ticket in enumerate(("a", "c")):
            self.history.add(replace(
                notification("walite"), received_at=index + 1,
                walite_activation=parse_activation(hint(
                    version=2, activation_id=ticket * 64,
                    expires_at=int(time.time()) + 3600,
                )),
            ))
        rows = [item.id for item in self.history.all()]
        used = []

        def navigate(metadata):
            self.assertNotIn(metadata.activation_id, used)
            used.append(metadata.activation_id)
            successor = replace(metadata, activation_id=str(len(used)) * 64)
            return WaliteActivationResult(successor, True)

        with patch.object(self.tray.walite_navigation, "send", side_effect=navigate), \
                patch.object(self.tray.walite_navigation, "availability",
                             return_value=(True, "Request discussion")), \
                patch.object(self.tray.walite, "find_window", return_value="0x123"), \
                patch.object(self.tray.walite, "raise_window") as focus:
            for row_id in rows * 2:
                stored = next(item for item in self.history.all() if item.id == row_id)
                self.tray._open_walite_discussion(stored)
                # A queued event still holding the consumed ticket cannot replay.
                self.tray._open_walite_discussion(stored)
                self.assertTrue(all(item.walite_activation for item in self.history.all()))
                card = self.tray.groups_box.get_children()[0]
                for message in card.messages.get_children():
                    controls = message.get_children()[-1].get_children()[-1]
                    self.assertTrue(any(child.get_label() == "Open discussion"
                                        and child.get_sensitive()
                                        for child in controls.get_children()))
            self.assertEqual(focus.call_count, 4)
        self.assertEqual(self.history.count(), 2)
        self.assertEqual(self.history.unread_count(), 2)

    def test_v2_queue_busy_preserves_fresh_ticket_without_focus(self):
        import time
        from dunst_tray.walite import parse_activation, WaliteActivationResult
        from test_walite import hint
        old = parse_activation(hint(version=2, expires_at=int(time.time()) + 3600))
        new = replace(old, activation_id="b" * 64)
        self.history.add(replace(notification("walite"), walite_activation=old))
        with patch.object(self.tray.walite_navigation, "send",
                          return_value=WaliteActivationResult(new, False)), \
                patch.object(self.tray.walite, "raise_window") as focus, \
                patch.object(self.tray, "_error") as error:
            self.tray._open_walite_discussion(self.history.latest())
            focus.assert_not_called()
            error.assert_called_once()
        self.assertEqual(self.history.latest().walite_activation, new)
        self.assertEqual(self.history.count(), 1)

    def test_failed_discussion_transport_does_not_focus_or_change_history(self):
        from dunst_tray.walite import parse_activation
        from test_walite import hint
        self.history.add(replace(notification("walite"),
                                 walite_activation=parse_activation(hint())))
        with patch.object(self.tray.walite, "find_window"), \
                patch.object(self.tray.walite, "raise_window") as focus, \
                patch.object(self.tray, "_error") as error:
            self.tray._open_walite_discussion(self.history.latest())
            focus.assert_not_called()
            error.assert_called_once()
            self.assertNotIn("activation_id", str(error.call_args))
        self.assertEqual(self.history.count(), 1)
        self.assertEqual(self.history.unread_count(), 1)

    def test_panel_bounds_background_alpha_and_corner_clipping(self):
        import cairo
        import time
        from dunst_tray.ui import Gtk
        self.tray._apply_appearance(replace(
            self.tray.config, panel_width=280, panel_height=300,
            panel_opacity=50, corner_radius=24,
        ))
        self.tray.toggle_center()
        for _ in range(20):
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            time.sleep(0.01)
        width, height = self.tray.window.get_size()
        self.assertEqual((width, height), (280, 300))
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.tray.window.draw(cairo.Context(surface))
        surface.flush()
        pixels = surface.get_data()
        if self.tray.window.get_screen().is_composited():
            self.assertEqual(pixels[3], 0)
            alpha = pixels[(height - 24) * surface.get_stride() + width // 2 * 4 + 3]
            self.assertGreaterEqual(alpha, 120)
            self.assertLessEqual(alpha, 140)
