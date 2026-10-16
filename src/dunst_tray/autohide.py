"""One event-driven inactivity deadline; no polling thread or accumulated timers."""

from __future__ import annotations

import math
import time
from contextlib import contextmanager


class InactivityTimer:
    def __init__(self, schedule, cancel, hide, clock=time.monotonic):
        self.schedule, self.cancel, self.hide = schedule, cancel, hide
        self.clock = clock
        self.enabled = False
        self.seconds = 5
        self.visible = False
        self.source = None
        self.deadline = 0.0
        self._holds = {}

    def _cancel(self):
        if self.source is not None:
            self.cancel(self.source)
            self.source = None

    def configure(self, enabled, seconds):
        self.enabled = bool(enabled)
        self.seconds = max(3, min(120, int(seconds)))
        self._cancel()
        self.activity()

    def opened(self):
        self.visible = True
        self.activity()

    def hidden(self):
        self.visible = False
        self._cancel()

    def activity(self):
        self.deadline = self.clock() + self.seconds
        if self.enabled and self.visible and not self._holds and self.source is None:
            self.source = self.schedule(self.seconds * 1000, self._expired)

    def pause(self, reason):
        self._holds[reason] = self._holds.get(reason, 0) + 1
        self._cancel()

    def resume(self, reason):
        count = self._holds.get(reason, 0)
        if count > 1:
            self._holds[reason] = count - 1
        elif count:
            del self._holds[reason]
        self.activity()

    @contextmanager
    def hold(self, reason):
        self.pause(reason)
        try:
            yield
        finally:
            self.resume(reason)

    def _expired(self):
        self.source = None
        if not self.enabled or not self.visible or self._holds:
            return False
        remaining = self.deadline - self.clock()
        if remaining > 0:
            self.source = self.schedule(max(1, math.ceil(remaining * 1000)),
                                        self._expired)
        else:
            self.hidden()
            self.hide()
        return False  # Always a one-shot GLib source.
