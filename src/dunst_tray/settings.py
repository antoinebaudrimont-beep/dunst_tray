"""Compact, nonblocking GTK appearance preferences for the companion panel."""

from __future__ import annotations

from dataclasses import replace

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from .config import AppConfig

RESTORE_DEFAULTS = 1001


class AppearanceDialog(Gtk.Dialog):
    """Edit draft values; only Apply asks the owner to persist them."""

    def __init__(self, parent, config: AppConfig, on_apply, on_closed):
        super().__init__(title="Notification Center Settings",
                         transient_for=parent, destroy_with_parent=True)
        self.set_resizable(False)
        self.base_config = config
        self.on_apply = on_apply
        self.on_closed = on_closed
        self.add_button("Restore Defaults", RESTORE_DEFAULTS)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Apply", Gtk.ResponseType.APPLY)
        self.set_default_response(Gtk.ResponseType.APPLY)
        content = self.get_content_area()
        content.set_border_width(16)
        content.set_spacing(12)
        grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        self.opacity = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 50, 100, 1
        )
        self.opacity.set_digits(0)
        self.opacity.set_value_pos(Gtk.PositionType.RIGHT)
        self.opacity.set_size_request(220, -1)
        self.width = Gtk.SpinButton.new_with_range(280, 550, 10)
        self.height = Gtk.SpinButton.new_with_range(300, 850, 10)
        self.radius = Gtk.SpinButton.new_with_range(0, 24, 1)
        for row, (label, widget) in enumerate((
            ("Background opacity (%)", self.opacity),
            ("Width (px)", self.width), ("Height (px)", self.height),
            ("Corner radius (px)", self.radius),
        )):
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            grid.attach(text, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)
        self.show_icons = Gtk.CheckButton(label="Show application icons")
        grid.attach(self.show_icons, 0, 4, 2, 1)
        self.auto_hide = Gtk.CheckButton(label="Automatically close notification center")
        self.auto_hide_timeout = Gtk.SpinButton.new_with_range(3, 120, 1)
        self.auto_hide.connect("toggled", lambda check:
                               self.auto_hide_timeout.set_sensitive(check.get_active()))
        grid.attach(self.auto_hide, 0, 5, 2, 1)
        timeout_label = Gtk.Label(label="Inactivity timeout (seconds)")
        timeout_label.set_xalign(0)
        grid.attach(timeout_label, 0, 6, 1, 1)
        grid.attach(self.auto_hide_timeout, 1, 6, 1, 1)
        content.pack_start(grid, False, False, 0)
        note = Gtk.Label(label=(
            "Changes apply to this notification center.\n"
            "Panel size fits the available screen space.\n"
            "Opacity and rounded corners need an X11 compositor."
        ))
        note.set_xalign(0)
        content.pack_start(note, False, False, 0)
        self.status = Gtk.Label()
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(52)
        content.pack_start(self.status, False, False, 0)
        self.load_values(config)
        self.connect("response", self._response)
        self.connect("destroy", lambda *_args: self.on_closed())
        self.show_all()

    def load_values(self, config: AppConfig):
        self.opacity.set_value(config.panel_opacity)
        self.width.set_value(config.panel_width)
        self.height.set_value(config.panel_height)
        self.radius.set_value(config.corner_radius)
        self.show_icons.set_active(config.show_icons)
        self.auto_hide.set_active(config.auto_hide)
        self.auto_hide_timeout.set_value(config.auto_hide_timeout)
        self.auto_hide_timeout.set_sensitive(config.auto_hide)

    def draft(self) -> AppConfig:
        return replace(
            self.base_config, panel_opacity=round(self.opacity.get_value()),
            panel_width=self.width.get_value_as_int(),
            panel_height=self.height.get_value_as_int(),
            corner_radius=self.radius.get_value_as_int(),
            show_icons=self.show_icons.get_active(),
            auto_hide=self.auto_hide.get_active(),
            auto_hide_timeout=self.auto_hide_timeout.get_value_as_int(),
        )

    def _response(self, _dialog, response):
        if response == RESTORE_DEFAULTS:
            self.load_values(AppConfig())
            self.status.set_text("Defaults loaded. Apply to save them.")
        elif response == Gtk.ResponseType.APPLY:
            try:
                self.base_config = self.on_apply(self.draft())
            except Exception as error:
                self.status.set_text(f"Could not save settings: {error}")
                return
            self.load_values(self.base_config)
            self.status.set_text("Saved. Settings updated.")
        else:
            self.destroy()
