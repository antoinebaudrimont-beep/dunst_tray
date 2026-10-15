from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dunst_tray.config import AppConfig, load_config


class ConfigTests(unittest.TestCase):
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
        self.assertEqual(config.panel_width, 900)
        self.assertEqual(config.panel_height, 250)
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


if __name__ == "__main__":
    unittest.main()

