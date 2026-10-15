"""Configuration loading and XDG path handling."""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated application settings."""

    history_limit: int = 100
    page_size: int = 5
    panel_width: int = 380
    panel_height: int = 680
    margin_top: int = 48
    margin_right: int = 16
    monitor_dbus: bool = True


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def data_home() -> Path:
    return Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )


def default_config_path() -> Path:
    return config_home() / "dunst-tray" / "config.ini"


def default_database_path() -> Path:
    return data_home() / "dunst-tray" / "history.sqlite3"


def _bounded_int(
    parser: configparser.ConfigParser,
    section: str,
    option: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = parser.getint(section, option, fallback=default)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration, applying conservative bounds to numeric values."""

    selected = path or default_config_path()
    parser = configparser.ConfigParser()
    if selected.is_file():
        parser.read(selected, encoding="utf-8")

    try:
        monitor_dbus = parser.getboolean(
            "capture", "monitor_dbus", fallback=True
        )
    except ValueError:
        monitor_dbus = True

    return AppConfig(
        history_limit=_bounded_int(
            parser, "history", "limit", 100, 10, 10_000
        ),
        page_size=_bounded_int(parser, "history", "page_size", 5, 1, 100),
        panel_width=_bounded_int(parser, "panel", "width", 380, 300, 900),
        panel_height=_bounded_int(parser, "panel", "height", 680, 250, 2_000),
        margin_top=_bounded_int(parser, "panel", "margin_top", 48, 0, 500),
        margin_right=_bounded_int(
            parser, "panel", "margin_right", 16, 0, 500
        ),
        monitor_dbus=monitor_dbus,
    )

