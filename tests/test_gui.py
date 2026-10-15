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
