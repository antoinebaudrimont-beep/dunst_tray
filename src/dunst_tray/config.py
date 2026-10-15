"""Configuration loading and XDG path handling."""

from __future__ import annotations

import configparser
import os
import tempfile
import logging
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
    panel_opacity: int = 97
    corner_radius: int = 14
    show_icons: bool = True


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
        try:
            parser.read(selected, encoding="utf-8")
        except (configparser.Error, UnicodeError):
            logging.getLogger(__name__).warning("Invalid settings; using defaults")
            parser = configparser.ConfigParser()

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
        panel_width=_bounded_int(parser, "panel", "width", 380, 280, 550),
        panel_height=_bounded_int(parser, "panel", "height", 680, 300, 850),
        margin_top=_bounded_int(parser, "panel", "margin_top", 48, 0, 500),
        margin_right=_bounded_int(
            parser, "panel", "margin_right", 16, 0, 500
        ),
        monitor_dbus=monitor_dbus,
        panel_opacity=_bounded_int(parser, "panel", "opacity", 97, 50, 100),
        corner_radius=_bounded_int(parser, "panel", "corner_radius", 14, 0, 24),
        show_icons=_boolean(parser, "panel", "show_icons", True),
    )


def _boolean(parser, section: str, option: str, default: bool) -> bool:
    try:
        return parser.getboolean(section, option, fallback=default)
    except ValueError:
        return default


def save_appearance(config: AppConfig, path: Path) -> AppConfig:
    """Atomically save appearance only, preserving unrelated sections/options."""
    parser = configparser.ConfigParser(interpolation=None)
    if path.exists():
        # Refuse to overwrite an unreadable or malformed existing config.
        with path.open(encoding="utf-8") as existing:
            parser.read_file(existing)
    if not parser.has_section("panel"):
        parser.add_section("panel")
    for option, value in {
        "width": max(280, min(550, config.panel_width)),
        "height": max(300, min(850, config.panel_height)),
        "opacity": max(50, min(100, config.panel_opacity)),
        "corner_radius": max(0, min(24, config.corner_radius)),
        "show_icons": str(config.show_icons).lower(),
    }.items():
        parser.set("panel", option, str(value))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".config-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            parser.write(target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return load_config(path)


def panel_geometry(config: AppConfig, workarea: tuple[int, int, int, int]):
    """Fit the preferred panel size and margins inside any monitor work area."""
    left, top, available_width, available_height = workarea
    available_width = max(1, available_width)
    available_height = max(1, available_height)
    right_margin = min(config.margin_right, available_width - 1)
    top_margin = min(config.margin_top, available_height - 1)
    width = min(config.panel_width, available_width - right_margin)
    height = min(config.panel_height, max(1, available_height - top_margin - 16))
    return (left + available_width - right_margin - width, top + top_margin,
            width, height)

