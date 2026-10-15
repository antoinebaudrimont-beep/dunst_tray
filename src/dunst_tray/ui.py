"""GTK3 tray icon and compact grouped notification center."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk  # noqa: E402

from .activation import (
    ActivationError, DesktopWindowActivator, WaliteWindowActivator, WindowActions,
)
from .applications import ApplicationCatalog
from .dunst import DunstControlError, DunstController
from .model import Notification
from .tray_icon import render_bell

if TYPE_CHECKING:
    from .config import AppConfig
    from .history import HistoryStore

LOGGER = logging.getLogger(__name__)

CSS = b"""
.notification-center {
  background: rgba(31, 31, 31, 0.97);
  border: 1px solid rgba(130, 130, 130, 0.65);
  border-radius: 14px;
  color: #f4f4f4;
}
.center-header { padding: 10px 12px 6px 12px; }
.center-title { font-size: 16px; font-weight: bold; }
.groups { padding: 4px 10px 12px 10px; }
.group-card {
  background: rgba(62, 62, 62, 0.92);
  border-radius: 10px;
  margin: 4px 0;
  padding: 3px;
}
.group-header { padding: 7px; }
.app-name { font-weight: bold; }
.latest-summary { color: #d1d1d1; }
.message { border-top: 1px solid rgba(140, 140, 140, 0.30); padding: 9px; }
.message-title { font-weight: bold; }
.message-body { color: #dddddd; }
.message-time { color: #aaaaaa; font-size: 9px; }
.empty { color: #bdbdbd; padding: 30px; }
button { color: #f4f4f4; }
"""


def _label(
    text: str,
    css_class: str | None = None,
    selectable: bool = False,
) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_xalign(0)
    label.set_line_wrap(True)
    label.set_line_wrap_mode(2)
    label.set_selectable(selectable)
    if css_class:
        label.get_style_context().add_class(css_class)
    return label


class GroupCard(Gtk.Box):
    """Expandable application group with incremental older-message access."""

    def __init__(
        self,
        app_name: str,
        notifications: list[Notification],
        page_size: int,
        can_activate,
        action_callback,
        applications: ApplicationCatalog,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("group-card")
        self.notifications = notifications
        self.page_size = page_size
        self.can_activate = can_activate
        self.visible_count = page_size
        self.action_callback = action_callback
        self.expanded = False

        self.header = Gtk.Button()
        self.header.set_relief(Gtk.ReliefStyle.NONE)
        self.header.get_style_context().add_class("group-header")
        self.header.connect("clicked", self._toggle)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        self.arrow = Gtk.Label(label="▸")
        header_box.pack_start(self.arrow, False, False, 0)
        header_box.pack_start(
            self._application_icon(notifications[0], applications),
            False, False, 0,
        )

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name = _label(f"{app_name} — {len(notifications)}", "app-name")
        latest_text = notifications[0].summary or notifications[0].body or "(empty)"
        latest = _label(latest_text, "latest-summary")
        latest.set_max_width_chars(35)
        latest.set_ellipsize(3)
        text_box.pack_start(name, False, False, 0)
        text_box.pack_start(latest, False, False, 0)
        header_box.pack_start(text_box, True, True, 0)
        self.header.add(header_box)
        self.pack_start(self.header, False, False, 0)

        self.messages = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.messages.set_no_show_all(True)
        self.pack_start(self.messages, False, False, 0)
        self._render_messages()

    @staticmethod
    def _application_icon(
        notification: Notification, applications: ApplicationCatalog,
    ) -> Gtk.Image:
        app = applications.resolve(notification)
        candidates = [notification.app_icon]
        if app is not None:
            candidates.extend((app.icon, app.desktop_id))
        theme = Gtk.IconTheme.get_default()
        for icon in candidates:
            if not icon:
                continue
            if Path(icon).is_absolute():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        icon, 38, 38, True
                    )
                    return Gtk.Image.new_from_pixbuf(pixbuf)
                except GLib.Error:
                    continue
            if theme and theme.has_icon(icon):
                image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
                image.set_pixel_size(38)
                return image
        return Gtk.Image.new_from_icon_name(
            "dialog-information-symbolic", Gtk.IconSize.DIALOG
        )

    def _toggle(self, _button: Gtk.Button) -> None:
        self.expanded = not self.expanded
        self.arrow.set_text("▾" if self.expanded else "▸")
        self.messages.set_visible(self.expanded)

    def _render_messages(self) -> None:
        for child in self.messages.get_children():
            self.messages.remove(child)

        for notification in self.notifications[: self.visible_count]:
            message = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            message.get_style_context().add_class("message")
            if notification.summary:
                message.pack_start(
                    _label(notification.summary, "message-title", True),
                    False,
                    False,
                    0,
                )
            if notification.body:
                message.pack_start(
                    _label(notification.body, "message-body", True),
                    False,
                    False,
                    0,
                )
            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            stamp = datetime.fromtimestamp(notification.received_at).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            footer.pack_start(_label(stamp, "message-time"), True, True, 0)
            if notification.has_default_action:
                action = Gtk.Button(label="Show app")
                action.set_relief(Gtk.ReliefStyle.NONE)
                actionable, explanation = self.can_activate(notification)
                action.set_sensitive(actionable)
                action.set_tooltip_text(explanation)
                action.connect(
                    "clicked",
                    lambda _button, item=notification: self.action_callback(item),
                )
                footer.pack_end(action, False, False, 0)
            message.pack_start(footer, False, False, 0)
            self.messages.pack_start(message, False, False, 0)

        remaining = len(self.notifications) - self.visible_count
        if remaining > 0:
            older = Gtk.Button(label=f"Show older ({remaining})")
            older.set_relief(Gtk.ReliefStyle.NONE)
            older.connect("clicked", self._show_older)
            self.messages.pack_start(older, False, False, 4)
        # The container has no-show-all so collapsed groups stay collapsed when
        # the parent window is shown. Explicitly reveal its children here.
        for child in self.messages.get_children():
            child.show_all()
        self.messages.set_visible(self.expanded)

    def _show_older(self, _button: Gtk.Button) -> None:
        self.visible_count += self.page_size
        self._render_messages()


class TrayApplication:
    """Own the tray UI while leaving notification rendering to Dunst."""

    def __init__(
        self,
        config: AppConfig,
        config_path: Path,
        history: HistoryStore,
        dunst: DunstController,
        quit_callback,
    ) -> None:
        self.config = config
        self.config_path = config_path
        self.history = history
        self.dunst = dunst
        self.walite = WaliteWindowActivator()
        self.applications = ApplicationCatalog()
        self.desktop = DesktopWindowActivator(self.applications)
        self.actions = WindowActions(self.walite, self.desktop)
        self.quit_callback = quit_callback
        self.unread = self.history.unread_count()
        self._icon_size = 22
        self._tray_color_widget = Gtk.Label()
        self._dunst_paused: bool | None = None
        self._syncing_pause = False

        self._install_css()
        self.window = self._build_window()
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_title("Dunst Tray")
        self.status_icon.set_visible(True)
        self.status_icon.connect("activate", self.toggle_center)
        self.status_icon.connect("popup-menu", self._show_menu)
        self.status_icon.connect("size-changed", self._tray_size_changed)
        settings = Gtk.Settings.get_default()
        self._theme_signals = []
        if settings:
            for setting in ("gtk-theme-name", "gtk-application-prefer-dark-theme"):
                signal_id = settings.connect(
                    f"notify::{setting}", lambda *_args: self._update_tray_icon()
                )
                self._theme_signals.append((settings, signal_id))
        self.menu, self.enabled_item = self._build_menu()
        self.refresh()
        self.refresh_dunst_state()

    @staticmethod
    def _install_css() -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

    def _build_window(self) -> Gtk.Window:
        window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        window.set_title("Notification Center")
        window.set_decorated(False)
        window.set_keep_above(True)
        window.set_skip_taskbar_hint(True)
        window.set_skip_pager_hint(True)
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        window.set_resizable(False)
        window.set_size_request(
            self.config.panel_width, self.config.panel_height
        )
        window.get_style_context().add_class("notification-center")
        window.connect("delete-event", self._hide_window)

        screen = window.get_screen()
        if screen and screen.is_composited():
            visual = screen.get_rgba_visual()
            if visual:
                window.set_visual(visual)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("center-header")
        title = _label("Notification Center", "center-title")
        header.pack_start(title, True, True, 0)
        clear = Gtk.Button(label="Clear all")
        clear.set_relief(Gtk.ReliefStyle.NONE)
        clear.connect("clicked", self._confirm_clear)
        header.pack_start(clear, False, False, 0)
        close = Gtk.Button.new_from_icon_name(
            "window-close-symbolic", Gtk.IconSize.BUTTON
        )
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.connect("clicked", lambda _button: window.hide())
        header.pack_start(close, False, False, 0)
        root.pack_start(header, False, False, 0)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.groups_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.groups_box.get_style_context().add_class("groups")
        scroller.add(self.groups_box)
        root.pack_start(scroller, True, True, 0)
        window.add(root)
        root.show_all()
        return window

    def _build_menu(self) -> tuple[Gtk.Menu, Gtk.CheckMenuItem]:
        menu = Gtk.Menu()
        enabled = Gtk.CheckMenuItem(label="Notifications enabled")
        enabled.connect("toggled", self._toggle_notifications)
        menu.append(enabled)

        open_item = Gtk.MenuItem(label="Open notification center")
        open_item.connect("activate", self.toggle_center)
        menu.append(open_item)

        replay = Gtk.MenuItem(label="Replay latest notification")
        replay.connect("activate", self._replay_latest)
        menu.append(replay)

        clear = Gtk.MenuItem(label="Clear notification history")
        clear.connect("activate", self._confirm_clear)
        menu.append(clear)

        settings = Gtk.MenuItem(label="Settings")
        settings.connect("activate", self._show_settings)
        menu.append(settings)

        menu.append(Gtk.SeparatorMenuItem())
        quit_item = Gtk.MenuItem(label="Quit tray application")
        quit_item.connect("activate", lambda _item: self.quit_callback())
        menu.append(quit_item)
        menu.show_all()
        return menu, enabled

    def _hide_window(self, *_args) -> bool:
        self.window.hide()
        return True

    def _position_window(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return
        workarea = monitor.get_workarea()
        height = min(
            self.config.panel_height,
            max(250, workarea.height - self.config.margin_top - 16),
        )
        self.window.set_size_request(self.config.panel_width, height)
        x = workarea.x + workarea.width - self.config.panel_width
        x -= self.config.margin_right
        y = workarea.y + self.config.margin_top
        self.window.move(max(workarea.x, x), y)

    def toggle_center(self, *_args) -> None:
        if self.window.get_visible():
            self.window.hide()
            return
        self.history.mark_all_read()
        self.refresh()
        self._position_window()
        self.window.show_all()
        self._position_window()

    def _tray_size_changed(self, _icon, size: int) -> bool:
        self._icon_size = size
        self._update_tray_icon()
        return True

    def _update_tray_icon(self) -> None:
        color = self._tray_color_widget.get_style_context().get_color(
            Gtk.StateFlags.NORMAL
        )
        self.status_icon.set_from_pixbuf(render_bell(
            self._icon_size, self.unread > 0, (color.red, color.green, color.blue),
        ))
        dnd = "unknown" if self._dunst_paused is None else (
            "on" if self._dunst_paused else "off"
        )
        self.status_icon.set_tooltip_text(
            f"Dunst Tray — {self.unread} unread, {self.history.count()} retained; "
            f"Do Not Disturb {dnd}"
        )

    def refresh(self) -> bool:
        self.actions.reset()
        self.unread = self.history.unread_count()
        for child in self.groups_box.get_children():
            self.groups_box.remove(child)
        groups = self.history.grouped()
        if not groups:
            empty = _label("No retained notifications", "empty")
            empty.set_justify(Gtk.Justification.CENTER)
            self.groups_box.pack_start(empty, False, False, 0)
        else:
            for app_name, notifications in groups.items():
                card = GroupCard(
                    app_name,
                    notifications,
                    self.config.page_size,
                    self._can_perform_action,
                    self._perform_action,
                    self.applications,
                )
                self.groups_box.pack_start(card, False, False, 0)
        self.groups_box.show_all()
        self._update_tray_icon()
        return False

    def notification_received(self) -> bool:
        # Arrivals while open stay unread until the next explicit opening.
        self.refresh()
        return False

    def _show_menu(
        self, icon: Gtk.StatusIcon, button: int, activate_time: int
    ) -> None:
        self.refresh_dunst_state()
        self.menu.popup(
            None,
            None,
            Gtk.StatusIcon.position_menu,
            icon,
            button,
            activate_time,
        )

    def refresh_dunst_state(self) -> None:
        try:
            enabled = not self.dunst.is_paused()
            self._syncing_pause = True
            self.enabled_item.set_active(enabled)
            self.enabled_item.set_sensitive(True)
            self._dunst_paused = not enabled
        except DunstControlError:
            self.enabled_item.set_sensitive(False)
            self._dunst_paused = None
        finally:
            self._syncing_pause = False
        self._update_tray_icon()

    def _toggle_notifications(self, item: Gtk.CheckMenuItem) -> None:
        if self._syncing_pause:
            return
        try:
            self.dunst.set_paused(not item.get_active())
        except DunstControlError as error:
            self._error("Could not change Do Not Disturb", str(error))
        self.refresh_dunst_state()

    def _replay_latest(self, _item: Gtk.MenuItem) -> None:
        try:
            self.dunst.replay_latest()
        except DunstControlError as error:
            self._error("Could not replay a notification", str(error))

    def _perform_action(self, notification: Notification) -> None:
        try:
            self.actions.activate(notification)
            self.window.hide()
        except ActivationError as error:
            self._error(
                f"Could not activate {notification.app_name}", str(error)
            )

    def _can_perform_action(self, notification: Notification) -> tuple[bool, str]:
        return self.actions.availability(notification)

    def _confirm_clear(self, _widget) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.CANCEL,
            text="Clear notification history?",
        )
        dialog.format_secondary_text(
            "This permanently removes the companion's saved notification "
            "text and Dunst's current history."
        )
        dialog.add_button("Clear", Gtk.ResponseType.OK)
        response = dialog.run()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.history.clear()
        try:
            self.dunst.clear_history()
        except DunstControlError as error:
            LOGGER.warning("Local history cleared; Dunst history failed: %s", error)
        self.refresh()

    def _show_settings(self, _item: Gtk.MenuItem) -> None:
        exists = self.config_path.is_file()
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.CLOSE,
            text="Dunst Tray settings",
        )
        detail = str(self.config_path)
        if not exists:
            detail += "\n\nThe file does not exist; built-in defaults are active."
        detail += "\n\nRestart Dunst Tray after editing the file."
        dialog.format_secondary_text(detail)
        dialog.run()
        dialog.destroy()

    def _error(self, title: str, detail: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE,
            text=title,
        )
        dialog.format_secondary_text(detail)
        dialog.run()
        dialog.destroy()

    def destroy(self) -> None:
        for settings, signal_id in self._theme_signals:
            settings.disconnect(signal_id)
        self.status_icon.set_visible(False)
        self.window.destroy()

