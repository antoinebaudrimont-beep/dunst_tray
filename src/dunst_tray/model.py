"""Application data models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .walite import WaliteActivation


@dataclass(frozen=True, slots=True)
class Notification:
    """One locally retained notification."""

    id: int | None
    received_at: float
    app_name: str
    replaces_id: int
    app_icon: str
    summary: str
    body: str
    actions: tuple[str, ...]
    urgency: int
    expire_timeout: int
    dunst_id: int | None = None
    desktop_entry: str = ""
    unread: bool = True
    walite_activation: WaliteActivation | None = field(default=None, repr=False)

    @property
    def has_default_action(self) -> bool:
        """Whether the sender advertised the standard default action."""

        return "default" in self.actions

