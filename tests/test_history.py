from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dunst_tray.history import HistoryStore
from dunst_tray.model import Notification


def notification(
    number: int,
    app_name: str = "Synthetic App",
    body: str | None = None,
) -> Notification:
    return Notification(
        id=None,
        received_at=float(number),
        app_name=app_name,
        replaces_id=0,
        app_icon="",
        summary=f"Title {number}",
        body=body if body is not None else f"Body {number}",
        actions=("default", "Open") if number % 2 else (),
        urgency=1,
        expire_timeout=5_000,
    )


class HistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        path = Path(self.temporary.name) / "private" / "history.sqlite3"
        self.store = HistoryStore(path, limit=5)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def test_retention_keeps_only_newest_records(self) -> None:
        for number in range(10):
            self.store.add(notification(number))

        retained = self.store.all()
        self.assertEqual(len(retained), 5)
        self.assertEqual(
            [item.summary for item in retained],
            ["Title 9", "Title 8", "Title 7", "Title 6", "Title 5"],
        )

    def test_identical_notifications_remain_individual_history_rows(self) -> None:
        first = notification(1, app_name="walite", body="Repeated")
        second = notification(2, app_name="walite", body="Repeated")
        self.store.add(first)
        self.store.add(second)

        grouped = self.store.grouped()
        self.assertEqual(len(grouped["walite"]), 2)

    def test_grouping_orders_apps_and_messages_by_recency(self) -> None:
        self.store.add(notification(1, app_name="Older App"))
        self.store.add(notification(2, app_name="Recent App"))
        self.store.add(notification(3, app_name="Older App"))

        grouped = self.store.grouped()
        self.assertEqual(list(grouped), ["Older App", "Recent App"])
        self.assertEqual(
            [item.received_at for item in grouped["Older App"]], [3.0, 1.0]
        )

    def test_dunst_id_update_and_clear(self) -> None:
        row_id = self.store.add(notification(1))
        self.store.set_dunst_id(row_id, 42)
        self.assertEqual(self.store.latest().dunst_id, 42)
        self.store.clear()
        self.assertEqual(self.store.count(), 0)
        self.assertIsNone(self.store.latest())


if __name__ == "__main__":
    unittest.main()

