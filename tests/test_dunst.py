from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from dunst_tray.dunst import DunstController, DunstControlError


class DunstControllerTests(unittest.TestCase):
    @patch("dunst_tray.dunst.subprocess.run")
    def test_current_action_uses_stack_position_zero(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        controller = DunstController("/usr/bin/dunstctl")

        controller.perform_current_action()

        run.assert_called_once_with(
            ["/usr/bin/dunstctl", "action", "0"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )

    @patch("dunst_tray.dunst.subprocess.run")
    def test_control_errors_include_dunstctl_message(self, run) -> None:
        run.return_value = subprocess.CompletedProcess([], 1, "", "not running")
        controller = DunstController("/usr/bin/dunstctl")

        with self.assertRaisesRegex(DunstControlError, "not running"):
            controller.is_paused()


if __name__ == "__main__":
    unittest.main()

