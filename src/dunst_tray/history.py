"""Bounded, private SQLite notification history."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path

from .model import Notification


class HistoryStore:
    """Persist notifications without storing D-Bus hints or sender metadata."""

    def __init__(self, path: Path, limit: int = 100) -> None:
        self.path = path
        self.limit = max(1, limit)
        self._lock = threading.RLock()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize()
        os.chmod(path, 0o600)

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    received_at REAL NOT NULL,
                    app_name TEXT NOT NULL,
                    replaces_id INTEGER NOT NULL DEFAULT 0,
                    app_icon TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    body TEXT NOT NULL DEFAULT '',
                    actions_json TEXT NOT NULL DEFAULT '[]',
                    urgency INTEGER NOT NULL DEFAULT 1,
                    expire_timeout INTEGER NOT NULL DEFAULT -1,
                    dunst_id INTEGER
                )
                """
            )

    def add(self, notification: Notification) -> int:
        """Insert one notification and trim only the oldest excess rows."""

        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO notifications (
                    received_at, app_name, replaces_id, app_icon, summary,
                    body, actions_json, urgency, expire_timeout, dunst_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.received_at,
                    notification.app_name,
                    notification.replaces_id,
                    notification.app_icon,
                    notification.summary,
                    notification.body,
                    json.dumps(notification.actions, ensure_ascii=False),
                    notification.urgency,
                    notification.expire_timeout,
                    notification.dunst_id,
                ),
            )
            row_id = int(cursor.lastrowid)
            self._connection.execute(
                """
                DELETE FROM notifications
                WHERE id NOT IN (
                    SELECT id FROM notifications
                    ORDER BY received_at DESC, id DESC
                    LIMIT ?
                )
                """,
                (self.limit,),
            )
        return row_id

    def set_dunst_id(self, row_id: int, dunst_id: int) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE notifications SET dunst_id = ? WHERE id = ?",
                (dunst_id, row_id),
            )

    def _row_to_model(self, row: sqlite3.Row) -> Notification:
        try:
            actions = tuple(json.loads(row["actions_json"]))
        except (json.JSONDecodeError, TypeError):
            actions = ()
        return Notification(
            id=int(row["id"]),
            received_at=float(row["received_at"]),
            app_name=str(row["app_name"]),
            replaces_id=int(row["replaces_id"]),
            app_icon=str(row["app_icon"]),
            summary=str(row["summary"]),
            body=str(row["body"]),
            actions=actions,
            urgency=int(row["urgency"]),
            expire_timeout=int(row["expire_timeout"]),
            dunst_id=(
                int(row["dunst_id"]) if row["dunst_id"] is not None else None
            ),
        )

    def all(self) -> list[Notification]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM notifications
                ORDER BY received_at DESC, id DESC
                """
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def grouped(self) -> OrderedDict[str, list[Notification]]:
        """Group by application, retaining newest-application-first order."""

        groups: OrderedDict[str, list[Notification]] = OrderedDict()
        for notification in self.all():
            groups.setdefault(notification.app_name, []).append(notification)
        return groups

    def latest(self) -> Notification | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT * FROM notifications
                ORDER BY received_at DESC, id DESC LIMIT 1
                """
            ).fetchone()
        return self._row_to_model(row) if row is not None else None

    def count(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS count FROM notifications"
            ).fetchone()
        return int(row["count"])

    def clear(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM notifications")
            self._connection.execute(
                "DELETE FROM sqlite_sequence WHERE name = 'notifications'"
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

