"""Pure helpers for the freedesktop notification protocol."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any

from .model import Notification
from .walite import parse_activation


def _unpack(value: Any) -> Any:
    unpack = getattr(value, "unpack", None)
    return unpack() if callable(unpack) else value


def parse_notify_call(
    values: Sequence[Any], received_at: float | None = None
) -> Notification:
    """Convert the body of a freedesktop Notify call into a safe model."""

    if len(values) != 8:
        raise ValueError("Notify calls must contain exactly eight arguments")

    (
        app_name,
        replaces_id,
        app_icon,
        summary,
        body,
        actions,
        hints,
        expire_timeout,
    ) = values

    urgency = 1
    if isinstance(hints, Mapping) and "urgency" in hints:
        try:
            urgency = int(_unpack(hints["urgency"]))
        except (TypeError, ValueError):
            urgency = 1

    clean_actions = tuple(str(item) for item in actions)
    desktop_entry = ""
    walite_activation = None
    if isinstance(hints, Mapping):
        identity = _unpack(hints.get("desktop-entry", ""))
        if isinstance(identity, str):
            desktop_entry = identity
        if str(app_name).strip().casefold() == "walite":
            walite_activation = parse_activation(
                _unpack(hints.get("x-walite-activation", ""))
            )
    return Notification(
        id=None,
        received_at=time.time() if received_at is None else received_at,
        app_name=str(app_name).strip() or "Unknown application",
        replaces_id=max(0, int(replaces_id)),
        app_icon=str(app_icon),
        summary=str(summary),
        body=str(body),
        actions=clean_actions,
        urgency=max(0, min(2, urgency)),
        expire_timeout=int(expire_timeout),
        desktop_entry=desktop_entry,
        walite_activation=walite_activation,
    )

