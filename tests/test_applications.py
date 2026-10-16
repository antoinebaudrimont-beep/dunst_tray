from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from dunst_tray.applications import ApplicationCatalog, desktop_executable
from test_activation import notification


class ApplicationCatalogTests(unittest.TestCase):
    def test_terminal_metadata_is_identity_only_not_a_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "org.example.Mail.desktop"
            path.write_text(
                "[Desktop Entry]\nType=Application\nName=Synthetic Mail\n"
                "Terminal=true\nExec=/usr/bin/synthetic-mail %u\n",
            )
            app = ApplicationCatalog([Path(directory)]).resolve(
                notification("Synthetic Mail"))
            self.assertTrue(app.terminal)
            self.assertEqual(app.executable, "synthetic-mail")
        for command in ('sh -c "evil"', 'python3 script.py', 'env A=b app',
                        '/usr/bin/python3.13 unrelated.py', 'java -jar other.jar',
                        '"unterminated', '%u'):
            self.assertEqual(desktop_executable(command), "")

    def test_user_desktop_icon_overrides_system_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            user = Path(directory) / "user"
            system = Path(directory) / "system"
            for folder, icon in ((user, "/icons/custom.svg"), (system, "chatgpt")):
                folder.mkdir()
                (folder / "chatgpt.desktop").write_text(
                    "[Desktop Entry]\nType=Application\nName=ChatGPT\n"
                    f"Icon={icon}\n", encoding="utf-8",
                )
            catalog = ApplicationCatalog([user, system])
            app = catalog.resolve(notification("ChatGPT"))
            self.assertIsNotNone(app)
            self.assertEqual(app.icon, "/icons/custom.svg")
            self.assertIn("chatgpt", app.window_classes)

    def test_desktop_hint_resolves_display_name_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "org.example.Client.desktop").write_text(
                "[Desktop Entry]\nType=Application\nName=Different name\n"
                "StartupWMClass=ExampleWindow\n", encoding="utf-8",
            )
            catalog = ApplicationCatalog([folder])
            item = replace(
                notification("Synthetic sender"),
                desktop_entry="org.example.Client.desktop",
            )
            app = catalog.resolve(item)
            self.assertIsNotNone(app)
            self.assertIn("examplewindow", app.window_classes)
            self.assertIsNone(catalog.resolve(notification("Unknown")))
