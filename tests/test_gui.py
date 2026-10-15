"""Opt-in GTK checks: DUNST_TRAY_GUI_TESTS=1; no real notification data."""

from __future__ import annotations

import os
import tempfile
import unittest
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
            pixbuf = self.Pixbuf.new(self._colorspace(), True, 8, 32, 32)
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

    def _colorspace(self):
        from dunst_tray.ui import GdkPixbuf
        return GdkPixbuf.Colorspace.RGB

    def test_synthetic_future_aerc_icon_uses_generic_desktop_metadata(self):
        self.catalog.applications.append(DesktopApplication(
            "aerc", "aerc", "utilities-terminal", frozenset({"aerc"}),
        ))
        image = self.image(replace(notification("aerc"), desktop_entry="aerc"))
        self.assertEqual(image.get_icon_name()[0], "utilities-terminal")
