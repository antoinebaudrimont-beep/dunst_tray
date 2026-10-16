from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from dunst_tray.config import AppConfig, load_config, panel_geometry, save_appearance


class ConfigTests(unittest.TestCase):
    def test_auto_hide_migration_persistence_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text("[panel]\nwidth=320\n[custom]\nkeep=yes\n")
            existing = load_config(path)
            self.assertFalse(existing.auto_hide)
            self.assertEqual(existing.auto_hide_timeout, 5)
            enabled = replace(existing, auto_hide=True, auto_hide_timeout=9)
            self.assertEqual(save_appearance(enabled, path), enabled)
            self.assertEqual(load_config(path), enabled)
            self.assertIn("keep = yes", path.read_text())
            for text, expected in (("1", 3), ("999", 120), ("bad", 5)):
                path.write_text("[panel]\nauto_hide=perhaps\n"
                                f"auto_hide_timeout={text}\n")
                config = load_config(path)
                self.assertFalse(config.auto_hide)
                self.assertEqual(config.auto_hide_timeout, expected)

    def test_missing_file_uses_defaults(self) -> None:
        config = load_config(Path("/path/that/does/not/exist"))
        self.assertEqual(config, AppConfig())

    def test_values_are_loaded_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(
                """
[history]
limit = 2
page_size = 12
[panel]
width = 99999
height = 100
margin_top = 72
margin_right = 22
[capture]
monitor_dbus = false
""",
                encoding="utf-8",
            )
            config = load_config(path)

        self.assertEqual(config.history_limit, 10)
        self.assertEqual(config.page_size, 12)
        self.assertEqual(config.panel_width, 550)
        self.assertEqual(config.panel_height, 300)
        self.assertEqual(config.margin_top, 72)
        self.assertEqual(config.margin_right, 22)
        self.assertFalse(config.monitor_dbus)

    def test_invalid_values_fall_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(
                """
[history]
limit = many
[capture]
monitor_dbus = perhaps
""",
                encoding="utf-8",
            )
            config = load_config(path)

        self.assertEqual(config.history_limit, 100)
        self.assertTrue(config.monitor_dbus)

    def test_appearance_persistence_preserves_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(
                "[history]\nlimit=250\n[capture]\nmonitor_dbus=false\n"
                "[panel]\nmargin_top=32\n[custom]\nvalue=keep-me\n",
                encoding="utf-8",
            )
            config = replace(load_config(path), panel_opacity=65,
                             panel_width=320, panel_height=450,
                             corner_radius=20, show_icons=False)
            saved = save_appearance(config, path)
            self.assertEqual(saved, config)
            self.assertEqual(load_config(path), config)
            self.assertIn("keep-me", path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.glob(".config-*")), [])

    def test_appearance_bounds_invalid_values_and_malformed_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text(
                "[panel]\nopacity=2\ncorner_radius=999\nshow_icons=perhaps\n",
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.panel_opacity, 50)
            self.assertEqual(config.corner_radius, 24)
            self.assertTrue(config.show_icons)
            path.write_text("malformed configuration", encoding="utf-8")
            with self.assertRaises(Exception):
                save_appearance(AppConfig(), path)
            self.assertEqual(path.read_text(), "malformed configuration")

    def test_panel_geometry_stays_inside_small_and_offset_monitors(self):
        for workarea in ((0, 24, 1440, 820), (-800, 50, 800, 600),
                         (0, 0, 240, 180), (0, 0, 1, 1)):
            x, y, width, height = panel_geometry(
                replace(AppConfig(), panel_width=550, panel_height=850), workarea
            )
            left, top, available_width, available_height = workarea
            self.assertGreaterEqual(x, left)
            self.assertGreaterEqual(y, top)
            self.assertLessEqual(x + width, left + available_width)
            self.assertLessEqual(y + height, top + available_height)


if __name__ == "__main__":
    unittest.main()

