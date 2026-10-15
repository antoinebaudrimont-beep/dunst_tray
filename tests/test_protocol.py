from __future__ import annotations

import unittest

from dunst_tray.protocol import parse_notify_call


class FakeVariant:
    def __init__(self, value):
        self.value = value

    def unpack(self):
        return self.value


class ProtocolTests(unittest.TestCase):
    def test_parses_notify_call_without_retaining_hints(self) -> None:
        parsed = parse_notify_call(
            (
                "walite",
                0,
                "/tmp/synthetic-icon.png",
                "Synthetic title",
                "Synthetic body",
                ["default", "Open"],
                {"urgency": FakeVariant(2), "sender-pid": FakeVariant(123)},
                15_000,
            ),
            received_at=1234.5,
        )

        self.assertEqual(parsed.app_name, "walite")
        self.assertEqual(parsed.urgency, 2)
        self.assertTrue(parsed.has_default_action)
        self.assertEqual(parsed.received_at, 1234.5)
        self.assertFalse(hasattr(parsed, "hints"))

    def test_empty_application_name_is_normalized(self) -> None:
        parsed = parse_notify_call(
            ("", 0, "", "", "", [], {}, -1), received_at=1
        )
        self.assertEqual(parsed.app_name, "Unknown application")

    def test_rejects_malformed_call(self) -> None:
        with self.assertRaises(ValueError):
            parse_notify_call(("too", "short"))


if __name__ == "__main__":
    unittest.main()

