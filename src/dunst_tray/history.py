"""Bounded, private SQLite notification history."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path

from .model import Notification
from .walite import parse_activation


class HistoryStore:
    """Persist display fields and desktop identity, without sender metadata."""

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
            columns = {
                row["name"] for row in self._connection.execute(
                    "PRAGMA table_info(notifications)"
                )
            }
            if "desktop_entry" not in columns:
                self._connection.execute(
                    "ALTER TABLE notifications ADD COLUMN "
                    "desktop_entry TEXT NOT NULL DEFAULT ''"
                )
            if "unread" not in columns:
                # Existing history has already been available for review. Do
                # not turn an upgrade into an invented backlog of unread mail.
                self._connection.execute(
                    "ALTER TABLE notifications ADD COLUMN "
                    "unread INTEGER NOT NULL DEFAULT 0"
                )
            if "walite_activation_json" not in columns:
                self._connection.execute(
                    "ALTER TABLE notifications ADD COLUMN "
                    "walite_activation_json TEXT NOT NULL DEFAULT ''"
                )

    def add(self, notification: Notification) -> int:
        """Insert one notification and trim only the oldest excess rows."""

        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO notifications (
                    received_at, app_name, replaces_id, app_icon, summary,
                    body, actions_json, urgency, expire_timeout, dunst_id,
                    desktop_entry, unread, walite_activation_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    notification.desktop_entry,
                    int(notification.unread),
                    notification.walite_activation.record_json()
                    if notification.walite_activation else "",
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
            desktop_entry=str(row["desktop_entry"]),
            unread=bool(row["unread"]),
            walite_activation=(
                parse_activation(str(row["walite_activation_json"]))
                if str(row["app_name"]).casefold() == "walite" else None
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

    def unread_count(self) -> int:
        with self._lock:
            return int(self._connection.execute(
                "SELECT COUNT(*) FROM notifications WHERE unread = 1"
            ).fetchone()[0])

    def mark_all_read(self) -> None:
        """Acknowledge the currently retained snapshot, not future arrivals."""
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE notifications SET unread = 0 WHERE unread = 1"
            )

    def take_walite_activation(self, notification: Notification) -> str | None:
        """Claim the exact one-use ticket; an opaque marker prevents stale saves."""
        if notification.walite_activation is None:
            return None
        claim = "in-flight:" + secrets.token_hex(16)
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE notifications SET walite_activation_json = ? "
                "WHERE id = ? AND walite_activation_json = ?",
                (claim, notification.id,
                 notification.walite_activation.record_json()),
            )
            return claim if cursor.rowcount == 1 else None

    def finish_walite_activation(self, row_id, claim, renewed=None) -> bool:
        """Save only into the still-claimed record; never resurrect cleared rows."""
        with self._lock, self._connection:
            cursor = self._connection.execute(
                "UPDATE notifications SET walite_activation_json = ? "
                "WHERE id = ? AND walite_activation_json = ?",
                (renewed.record_json() if renewed else "", row_id, claim),
            )
            return cursor.rowcount == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()

