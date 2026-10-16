from __future__ import annotations

import subprocess
import unittest
from dataclasses import replace

from dunst_tray.activation import (
    ActivationError, DesktopWindowActivator, WaliteWindowActivator, WindowActions,
)
from dunst_tray.applications import ApplicationCatalog, DesktopApplication
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


class DesktopActivationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = ApplicationCatalog([])
        self.catalog.applications.append(DesktopApplication(
            "chatgpt", "ChatGPT", "chatgpt", frozenset({"chatgpt"}),
        ))
        self.calls = []

    def runner(self, arguments):
        call = tuple(arguments)
        self.calls.append(call)
        output = ""
        if call == ("wmctrl", "-l"):
            # A matching title must not override the actual WM_CLASS.
            output = "0x200001 0 host ChatGPT\n0x200002 0 host Renamed\n"
        elif call == ("xprop", "-id", "0x200001", "WM_CLASS"):
            output = 'WM_CLASS(STRING) = "terminal", "Terminal"\n'
        elif call == ("xprop", "-id", "0x200002", "WM_CLASS"):
            output = (
                'WM_CLASS(STRING) = "chatgpt (/tmp/profile)", "Chatgpt"\n'
            )
        return subprocess.CompletedProcess(call, 0, output, "")

    def test_expired_saved_entry_raises_matching_class_not_title(self) -> None:
        activator = DesktopWindowActivator(
            self.catalog, wmctrl="wmctrl", xprop="xprop", display=":0",
            runner=self.runner,
        )
        old = replace(notification("ChatGPT"), id=1, received_at=0)
        self.assertTrue(activator.can_activate(old))
        activator.activate(old)
        self.assertIn(("wmctrl", "-i", "-a", "0x200002"), self.calls)
        self.assertNotIn(("wmctrl", "-i", "-a", "0x200001"), self.calls)

    def test_missing_application_window_reports_failure(self) -> None:
        self.catalog.applications[0] = DesktopApplication(
            "chatgpt", "ChatGPT", "chatgpt", frozenset({"no-such-class"}),
        )
        activator = DesktopWindowActivator(
            self.catalog, wmctrl="wmctrl", xprop="xprop", display=":0",
            runner=self.runner,
        )
        with self.assertRaisesRegex(ActivationError, "No running ChatGPT"):
            activator.activate(notification("ChatGPT"))
        self.assertFalse(any(call[:3] == ("wmctrl", "-i", "-a")
                             for call in self.calls))

    def test_unknown_targets_disabled_but_default_action_not_required(self):
        desktop = DesktopWindowActivator(
            self.catalog, wmctrl="wmctrl", xprop="xprop", display=":0",
            runner=self.runner,
        )
        actions = WindowActions(WaliteWindowActivator(display=""), desktop)
        self.assertFalse(actions.availability(
            notification("Unknown future application"))[0])
        self.assertTrue(actions.availability(
            replace(notification("ChatGPT"), actions=()))[0])
        self.assertTrue(actions.availability(notification("ChatGPT"))[0])
        # Two same-application windows must not silently select one.
        desktop.runner = lambda args: subprocess.CompletedProcess(
            args, 0,
            "0x200001 0 host A\n0x200002 0 host B\n"
            if args[-1] == "-l" else 'WM_CLASS(STRING) = "app", "Chatgpt"',
            "",
        )
        actions.reset()
        available, reason = actions.availability(notification("ChatGPT"))
        self.assertFalse(available)
        self.assertIn("More than one", reason)

    def test_future_aerc_without_verified_window_is_disabled(self):
        self.catalog.applications.append(DesktopApplication(
            "aerc", "aerc", "utilities-terminal", frozenset({"aerc"}),
        ))
        desktop = DesktopWindowActivator(
            self.catalog, wmctrl="wmctrl", xprop="xprop", display=":0",
            runner=self.runner,
        )
        actions = WindowActions(WaliteWindowActivator(display=""), desktop)
        self.assertFalse(actions.availability(notification("aerc"))[0])
        with self.assertRaises(ActivationError):
            actions.activate(notification("aerc"))
        self.assertFalse(any(call[:3] == ("wmctrl", "-i", "-a")
                             for call in self.calls))


if __name__ == "__main__":
    unittest.main()

