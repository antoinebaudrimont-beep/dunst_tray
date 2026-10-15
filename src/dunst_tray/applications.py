"""Resolve notification identities against installed desktop applications."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path

from .model import Notification


@dataclass(frozen=True, slots=True)
class DesktopApplication:
    desktop_id: str
    name: str
    icon: str
    window_classes: frozenset[str]


class ApplicationCatalog:
    """Read desktop metadata without executing desktop-file commands."""

    def __init__(self, directories: list[Path] | None = None) -> None:
        if directories is None:
            data_home = Path(
                os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")
            )
            data_dirs = os.environ.get(
                "XDG_DATA_DIRS", "/usr/local/share:/usr/share"
            ).split(os.pathsep)
            directories = [data_home / "applications"] + [
                Path(directory) / "applications"
                for directory in data_dirs if directory
            ]
        self.applications: list[DesktopApplication] = []
        seen: set[str] = set()
        for directory in directories:
            for desktop_file in sorted(directory.rglob("*.desktop")):
                desktop_id = str(desktop_file.relative_to(directory)).replace(
                    os.sep, "-"
                )[:-8]
                if desktop_id in seen:
                    continue
                seen.add(desktop_id)
                parser = configparser.ConfigParser(interpolation=None)
                try:
                    parser.read(desktop_file, encoding="utf-8")
                    entry = parser["Desktop Entry"]
                    if (
                        entry.get("Type") != "Application"
                        or entry.getboolean("Hidden", False)
                    ):
                        continue
                    name = entry.get("Name", desktop_id)
                    classes = {desktop_id.casefold()}
                    startup_class = entry.get("StartupWMClass", "")
                    if startup_class:
                        classes.add(startup_class.casefold())
                    self.applications.append(DesktopApplication(
                        desktop_id, name, entry.get("Icon", ""),
                        frozenset(classes),
                    ))
                except (OSError, UnicodeError, configparser.Error, KeyError,
                        ValueError):
                    continue

    def resolve(self, notification: Notification) -> DesktopApplication | None:
        desktop_id = notification.desktop_entry.removesuffix(".desktop")
        if desktop_id:
            return next((
                app for app in self.applications
                if app.desktop_id == desktop_id
            ), None)
        name = notification.app_name.casefold()
        matches = [
            app for app in self.applications
            if name in (app.name.casefold(), app.desktop_id.casefold())
        ]
        return matches[0] if len(matches) == 1 else None
