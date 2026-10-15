from __future__ import annotations

import subprocess
import unittest

from dunst_tray.activation import ActivationError, WaliteWindowActivator
from dunst_tray.model import Notification


def notification(app_name: str = "walite") -> Notification:
    return Notification(
        id=1,
        received_at=1,
        app_name=app_name,
        replaces_id=0,
        app_icon="",
        summary="Synthetic title",
        body="Synthetic body",
        actions=("default", "Open"),
        urgency=1,
        expire_timeout=15_000,
        dunst_id=9,
    )


class CommandFixture:
    marker = "0123456789abcdef0123456789abcdef"

    def __init__(self, marked: tuple[str, ...] = ("0x200002",)) -> None:
        self.marked = marked
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, arguments) -> subprocess.CompletedProcess[str]:
        call = tuple(arguments)
        self.calls.append(call)
        if call == ("wmctrl", "-l"):
            return subprocess.CompletedProcess(
                call,
                0,
                "0x200001  0 host Other\n0x200002  0 host Walite\n",
                "",
            )
        if call[:2] == ("xprop", "-id"):
            window_id = call[2]
            output = 'WM_CLASS(STRING) = "kitty", "kitty"\n'
            if window_id in self.marked:
                output += (
                    f"_WALITE_NOTIFICATION_{self.marker}(STRING) = "
                    f'"{self.marker}"\n'
                )
            return subprocess.CompletedProcess(call, 0, output, "")
        if call[:3] == ("wmctrl", "-i", "-a"):
            return subprocess.CompletedProcess(call, 0, "", "")
        return subprocess.CompletedProcess(call, 1, "", "unexpected command")


class WaliteActivationTests(unittest.TestCase):
    def test_all_retained_walite_actions_are_eligible(self) -> None:
        activator = WaliteWindowActivator(
            "wmctrl", "xprop", ":0", CommandFixture()
        )

        self.assertTrue(activator.can_activate(notification()))
        self.assertFalse(activator.can_activate(notification("Other App")))

    def test_marked_walite_window_is_raised(self) -> None:
        fixture = CommandFixture()
        activator = WaliteWindowActivator("wmctrl", "xprop", ":0", fixture)

        activator.activate(notification())

        self.assertIn(("wmctrl", "-i", "-a", "0x200002"), fixture.calls)

    def test_missing_or_ambiguous_window_is_not_guessed(self) -> None:
        for marked in ((), ("0x200001", "0x200002")):
            with self.subTest(marked=marked):
                activator = WaliteWindowActivator(
                    "wmctrl", "xprop", ":0", CommandFixture(marked)
                )
                with self.assertRaises(ActivationError):
                    activator.activate(notification())

    def test_marker_name_and_value_must_match(self) -> None:
        marker = "0123456789abcdef0123456789abcdef"
        other = "fedcba9876543210fedcba9876543210"
        properties = (
            f'_WALITE_NOTIFICATION_{marker}(STRING) = "{other}"\n'
        )
        self.assertFalse(WaliteWindowActivator._has_walite_marker(properties))


if __name__ == "__main__":
    unittest.main()

