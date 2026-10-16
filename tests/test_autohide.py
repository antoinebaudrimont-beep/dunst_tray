from __future__ import annotations

import unittest

from dunst_tray.autohide import InactivityTimer


class Scheduler:
    def __init__(self):
        self.now = 0
        self.next_id = 0
        self.pending = {}
        self.hidden = 0

    def schedule(self, milliseconds, callback):
        self.next_id += 1
        self.pending[self.next_id] = (self.now + milliseconds / 1000, callback)
        return self.next_id

    def cancel(self, source):
        del self.pending[source]

    def hide(self):
        self.hidden += 1

    def advance(self, seconds):
        self.now += seconds
        for source, (deadline, callback) in list(self.pending.items()):
            if deadline <= self.now:
                del self.pending[source]
                self.assert_one_shot(callback())

    @staticmethod
    def assert_one_shot(result):
        assert result is False


class InactivityTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler()
        self.timer = InactivityTimer(
            self.scheduler.schedule, self.scheduler.cancel, self.scheduler.hide,
            clock=lambda: self.scheduler.now,
        )

    def test_disabled_default_never_schedules_or_hides(self):
        self.timer.opened()
        self.scheduler.advance(1000)
        self.assertEqual(self.scheduler.pending, {})
        self.assertEqual(self.scheduler.hidden, 0)

    def test_default_enabled_delay_and_activity_extends_single_deadline(self):
        self.timer.configure(True, 5)
        self.timer.opened()
        self.scheduler.advance(4)
        for _ in range(1000):
            self.timer.activity()
        self.assertEqual(len(self.scheduler.pending), 1)
        self.scheduler.advance(1)
        self.assertEqual(self.scheduler.hidden, 0)
        self.assertEqual(len(self.scheduler.pending), 1)
        self.scheduler.advance(4)
        self.assertEqual(self.scheduler.hidden, 1)
        self.assertIsNone(self.timer.source)

    def test_settings_pointer_modal_and_nested_transactions_suspend(self):
        self.timer.configure(True, 3)
        self.timer.opened()
        for reason in ("settings", "pointer", "menu", "transaction"):
            self.timer.pause(reason)
        self.scheduler.advance(300)
        self.assertEqual(self.scheduler.hidden, 0)
        self.assertEqual(self.scheduler.pending, {})
        for reason in ("settings", "pointer", "menu"):
            self.timer.resume(reason)
        self.timer.pause("transaction")
        self.timer.resume("transaction")
        self.assertEqual(self.scheduler.pending, {})
        self.timer.resume("transaction")
        self.scheduler.advance(3)
        self.assertEqual(self.scheduler.hidden, 1)

    def test_reopen_reconfigure_disable_and_exception_cleanup(self):
        self.timer.configure(True, 3)
        for _ in range(20):
            self.timer.opened()
            self.assertEqual(len(self.scheduler.pending), 1)
            self.timer.hidden()
            self.assertEqual(self.scheduler.pending, {})
        self.timer.opened()
        with self.assertRaises(RuntimeError):
            with self.timer.hold("transaction"):
                raise RuntimeError("synthetic error")
        self.assertEqual(len(self.scheduler.pending), 1)
        self.timer.configure(False, 5)
        self.assertEqual(self.scheduler.pending, {})
        self.scheduler.advance(300)
        self.assertEqual(self.scheduler.hidden, 0)

    def test_bounds_and_settings_apply_does_not_bypass_hold(self):
        self.timer.pause("settings")
        self.timer.configure(True, 1)
        self.assertEqual(self.timer.seconds, 3)
        self.timer.opened()
        self.assertEqual(self.scheduler.pending, {})
        self.timer.configure(True, 1000)
        self.assertEqual(self.timer.seconds, 120)
        self.timer.resume("settings")
        self.scheduler.advance(119)
        self.assertEqual(self.scheduler.hidden, 0)
        self.scheduler.advance(1)
        self.assertEqual(self.scheduler.hidden, 1)
