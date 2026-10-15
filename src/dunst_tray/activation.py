"""Durable application-specific activation helpers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence

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


class WaliteWindowActivator:
    """Find and focus the X11 window marked by a running Walite instance."""

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

    @staticmethod
    def handles(notification: Notification) -> bool:
        """Whether this adapter understands the notification's application."""

        return notification.app_name.casefold() == "walite"

    @property
    def available(self) -> bool:
        return bool(self.display and self.wmctrl and self.xprop)

    def can_activate(self, notification: Notification) -> bool:
        return (
            notification.has_default_action
            and self.handles(notification)
            and self.available
        )

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
        self._run(self.wmctrl, "-i", "-a", window_id)

