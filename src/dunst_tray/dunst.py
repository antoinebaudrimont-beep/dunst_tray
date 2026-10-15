"""Small, on-demand wrapper around dunstctl."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


class DunstControlError(RuntimeError):
    """Raised when Dunst cannot be controlled."""


@dataclass(slots=True)
class DunstController:
    executable: str | None = None

    def __post_init__(self) -> None:
        self.executable = self.executable or shutil.which("dunstctl")

    def _run(self, *arguments: str) -> str:
        if not self.executable:
            raise DunstControlError("dunstctl is not installed")
        try:
            result = subprocess.run(
                [self.executable, *arguments],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise DunstControlError(str(error)) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise DunstControlError(detail or "dunstctl failed")
        return result.stdout.strip()

    def is_paused(self) -> bool:
        return self._run("is-paused").lower() == "true"

    def set_paused(self, paused: bool) -> None:
        self._run("set-paused", "true" if paused else "false")

    def replay_latest(self) -> None:
        self._run("history-pop")

    def clear_history(self) -> None:
        self._run("history-clear")

    def perform_current_action(self) -> None:
        """Invoke the topmost visible notification's default action."""

        self._run("action", "0")

