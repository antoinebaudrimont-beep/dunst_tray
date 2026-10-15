"""Command-line entry point."""

from __future__ import annotations

import argparse
import fcntl
import logging
import os
import signal
import sys
from pathlib import Path
from typing import IO

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from . import __version__
from .capture import NotificationMonitor
from .config import (
    default_config_path,
    default_database_path,
    load_config,
)
from .dunst import DunstController
from .history import HistoryStore
from .ui import TrayApplication

LOGGER = logging.getLogger(__name__)


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight tray and notification center for Dunst"
    )
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--database", type=Path, default=default_database_path())
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    return parser.parse_args(argv)


def _acquire_instance_lock() -> IO[str]:
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    lock_path = runtime / f"dunst-tray-{os.getuid()}.lock"
    handle = lock_path.open("w", encoding="utf-8")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        handle.close()
        raise RuntimeError("dunst-tray is already running") from error
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        lock_handle = _acquire_instance_lock()
    except (OSError, RuntimeError) as error:
        LOGGER.error("%s", error)
        return 1

    config = load_config(args.config)
    try:
        history = HistoryStore(args.database, config.history_limit)
    except (OSError, ValueError) as error:
        LOGGER.error("Cannot open private notification history: %s", error)
        lock_handle.close()
        return 1

    monitor: NotificationMonitor | None = None
    stopping = False

    def stop() -> bool:
        nonlocal stopping
        if stopping:
            return False
        stopping = True
        if monitor is not None:
            monitor.stop()
        tray.destroy()
        history.close()
        lock_handle.close()
        Gtk.main_quit()
        return False

    tray = TrayApplication(
        config,
        args.config,
        history,
        DunstController(),
        stop,
    )
    if config.monitor_dbus:
        monitor = NotificationMonitor(history, tray.notification_received)
        try:
            monitor.start()
        except GLib.Error as error:
            LOGGER.error(
                "Passive D-Bus monitoring is unavailable; history capture "
                "is disabled: %s",
                error,
            )
            monitor = None

    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, stop)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, stop)
    try:
        Gtk.main()
    except KeyboardInterrupt:
        stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

