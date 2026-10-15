"""Passive D-Bus capture that never claims the notification service name."""

from __future__ import annotations

import logging
from collections.abc import Callable

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib  # noqa: E402

from .history import HistoryStore
from .protocol import parse_notify_call

LOGGER = logging.getLogger(__name__)


class NotificationMonitor:
    """Observe Notify calls over a dedicated monitor-only bus connection."""

    def __init__(
        self,
        history: HistoryStore,
        on_notification: Callable[[], None],
    ) -> None:
        self.history = history
        self.on_notification = on_notification
        self.connection: Gio.DBusConnection | None = None
        self.filter_id: int | None = None
        self._pending: dict[tuple[str, int], int] = {}

    def start(self) -> None:
        address = Gio.dbus_address_get_for_bus_sync(
            Gio.BusType.SESSION, None
        )
        flags = (
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT
            | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION
        )
        connection = Gio.DBusConnection.new_for_address_sync(
            address, flags, None, None
        )
        rules = [
            "type='method_call',"
            "interface='org.freedesktop.Notifications',member='Notify'",
            "type='method_return'",
        ]
        connection.call_sync(
            "org.freedesktop.DBus",
            "/org/freedesktop/DBus",
            "org.freedesktop.DBus.Monitoring",
            "BecomeMonitor",
            GLib.Variant("(asu)", (rules, 0)),
            None,
            Gio.DBusCallFlags.NONE,
            3_000,
            None,
        )
        self.connection = connection
        self.filter_id = connection.add_filter(self._filter, None)
        LOGGER.info("Passive notification monitoring started")

    def _filter(
        self,
        _connection: Gio.DBusConnection,
        message: Gio.DBusMessage,
        _incoming: bool,
        _user_data: object,
    ) -> Gio.DBusMessage:
        try:
            message_type = message.get_message_type()
            if message_type == Gio.DBusMessageType.METHOD_CALL:
                self._handle_call(message)
            elif message_type == Gio.DBusMessageType.METHOD_RETURN:
                self._handle_return(message)
        except Exception:
            LOGGER.exception("Ignored malformed notification bus message")
        return message

    def _handle_call(self, message: Gio.DBusMessage) -> None:
        if (
            message.get_interface() != "org.freedesktop.Notifications"
            or message.get_member() != "Notify"
        ):
            return
        body = message.get_body()
        if body is None:
            return
        notification = parse_notify_call(body.unpack())
        row_id = self.history.add(notification)
        sender = message.get_sender()
        if sender:
            self._pending[(sender, message.get_serial())] = row_id
        GLib.idle_add(self.on_notification)

    def _handle_return(self, message: Gio.DBusMessage) -> None:
        destination = message.get_destination()
        if not destination:
            return
        row_id = self._pending.pop(
            (destination, message.get_reply_serial()), None
        )
        if row_id is None:
            return
        body = message.get_body()
        if body is None:
            return
        values = body.unpack()
        if len(values) == 1 and isinstance(values[0], int):
            self.history.set_dunst_id(row_id, values[0])

    def stop(self) -> None:
        if self.connection is None:
            return
        if self.filter_id is not None:
            self.connection.remove_filter(self.filter_id)
        self.connection.close_sync(None)
        self.connection = None
        self.filter_id = None
        self._pending.clear()

