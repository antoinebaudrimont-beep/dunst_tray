"""Durable application-specific activation helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence

from .applications import ApplicationCatalog
from .model import Notification

WINDOW_ID = re.compile(r"^0x[0-9a-fA-F]+$")
WALITE_MARKER = re.compile(
    r'^_WALITE_NOTIFICATION_([0-9a-fA-F]{32})\(STRING\) = '
    r'"([0-9a-fA-F]{32})"$'
)


class ActivationError(RuntimeError):
    """Raised when a retained notification cannot activate its application."""


CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def _run_command(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(arguments),
        check=False,
        capture_output=True,
        text=True,
        timeout=3,
    )


class X11WindowActivator:
    """Bounded command execution and X11 window enumeration."""

    def __init__(
        self,
        wmctrl: str | None = None,
        xprop: str | None = None,
        display: str | None = None,
        runner: CommandRunner = _run_command,
    ) -> None:
        self.wmctrl = wmctrl if wmctrl is not None else shutil.which("wmctrl")
        self.xprop = xprop if xprop is not None else shutil.which("xprop")
        self.display = display if display is not None else os.environ.get("DISPLAY")
        self.runner = runner

    @property
    def available(self) -> bool:
        return bool(self.display and self.wmctrl and self.xprop)

    def _run(self, *arguments: str) -> str:
        try:
            result = self.runner(arguments)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ActivationError(str(error)) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or "desktop command failed"
            raise ActivationError(detail)
        return result.stdout

    def _window_ids(self) -> list[str]:
        if not self.wmctrl:
            return []
        output = self._run(self.wmctrl, "-l")
        window_ids: list[str] = []
        for line in output.splitlines():
            fields = line.split(maxsplit=1)
            if fields and WINDOW_ID.fullmatch(fields[0]):
                window_ids.append(fields[0].lower())
        return window_ids

    def raise_window(self, window_id: str) -> None:
        if not self.wmctrl:
            raise ActivationError("X11 activation tools are unavailable")
        self._run(self.wmctrl, "-i", "-a", window_id)


class WaliteWindowActivator(X11WindowActivator):
    """Find and focus the X11 window marked by a running Walite instance."""

    @staticmethod
    def handles(notification: Notification) -> bool:
        return notification.app_name.casefold() == "walite"

    def can_activate(self, notification: Notification) -> bool:
        return (
            notification.has_default_action
            and self.handles(notification)
            and self.available
        )

    @staticmethod
    def _has_walite_marker(properties: str) -> bool:
        for line in properties.splitlines():
            match = WALITE_MARKER.fullmatch(line.strip())
            if match and match.group(1).casefold() == match.group(2).casefold():
                return True
        return False

    def find_window(self) -> str:
        """Return the sole currently marked Walite window."""

        if not self.available or not self.xprop:
            raise ActivationError("Walite X11 activation tools are unavailable")
        matches: list[str] = []
        for window_id in self._window_ids():
            try:
                properties = self._run(self.xprop, "-id", window_id)
            except ActivationError:
                continue
            if self._has_walite_marker(properties):
                matches.append(window_id)
        if not matches:
            raise ActivationError("No running Walite window was found")
        if len(matches) > 1:
            raise ActivationError("More than one marked Walite window was found")
        return matches[0]

    def activate(self, notification: Notification) -> None:
        """Raise the marked Walite window for any retained Walite message."""

        if not self.can_activate(notification) or not self.wmctrl:
            raise ActivationError("This is not an actionable Walite notification")
        window_id = self.find_window()
        self.raise_window(window_id)


class DesktopWindowActivator(X11WindowActivator):
    """Raise windows identified by installed desktop application metadata."""

    def __init__(self, catalog: ApplicationCatalog, **kwargs) -> None:
        super().__init__(**kwargs)
        self.catalog = catalog

    def can_activate(self, notification: Notification) -> bool:
        return bool(
            self.available and notification.has_default_action
            and self.catalog.resolve(notification)
        )

    def find_window(self, notification: Notification) -> str:
        """Resolve one exact application window, without activating it."""

        app = self.catalog.resolve(notification)
        if not self.can_activate(notification) or app is None or not self.xprop:
            raise ActivationError("Application window identity is unavailable")
        matches = []
        for window_id in self._window_ids():
            try:
                output = self._run(self.xprop, "-id", window_id, "WM_CLASS")
            except ActivationError:
                continue
            # xprop quotes both resource name and class; preserve spaces in
            # Electron resource names rather than splitting wmctrl columns.
            values = re.findall(r'"(?:[^"\\]|\\.)*"', output)
            try:
                classes = {json.loads(value).casefold() for value in values}
            except (ValueError, AttributeError):
                continue
            if classes & app.window_classes:
                matches.append(window_id)
        if not matches:
            raise ActivationError(f"No running {app.name} window was found")
        if len(matches) > 1:
            raise ActivationError(
                f"More than one {app.name} window was found"
            )
        return matches[0]

    def activate(self, notification: Notification) -> None:
        self.raise_window(self.find_window(notification))


class WindowActions:
    """Describe verified application focus separately from message callbacks."""

    def __init__(self, walite, desktop) -> None:
        self.walite = walite
        self.desktop = desktop
        self.reset()

    def reset(self) -> None:
        self._availability: dict[tuple[str, str], tuple[bool, str]] = {}

    def adapter(self, notification: Notification):
        return next((
            adapter for adapter in (self.walite, self.desktop)
            if adapter.can_activate(notification)
        ), None)

    def availability(self, notification: Notification) -> tuple[bool, str]:
        if not notification.has_default_action:
            return False, "The sender did not provide an action."
        key = (notification.app_name, notification.desktop_entry)
        if key not in self._availability:
            adapter = self.adapter(notification)
            if adapter is None:
                result = (False,
                          "No reliable application window target is available. "
                          "Saved message callbacks cannot be replayed safely.")
            else:
                try:
                    if adapter is self.walite:
                        adapter.find_window()
                    else:
                        adapter.find_window(notification)
                    result = (True, "Raise the application window; this does "
                              "not select the original message.")
                except ActivationError as error:
                    result = (False, str(error))
            self._availability[key] = result
        return self._availability[key]

    def activate(self, notification: Notification) -> None:
        adapter = self.adapter(notification)
        if adapter is None:
            raise ActivationError("No reliable application window target")
        # Re-resolve at click time: a window may have closed since rendering.
        adapter.activate(notification)

