"""Clip the entire notification center to its rounded X11 surface."""

from __future__ import annotations

import math

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_foreign("cairo")
from gi.repository import Gtk  # noqa: E402


class PanelWindow(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.corner_radius = 14
        self.set_app_paintable(True)
        screen = self.get_screen()
        if screen and screen.get_rgba_visual():
            self.set_visual(screen.get_rgba_visual())
        self.connect("size-allocate", lambda *_args: self.update_input_shape())
        self.connect("realize", lambda *_args: self.update_input_shape())

    def effective_radius(self):
        screen = self.get_screen()
        if not screen or not screen.is_composited():
            return 0
        return min(self.corner_radius, self.get_allocated_width() / 2,
                   self.get_allocated_height() / 2)

    def do_draw(self, context):
        width, height = self.get_allocated_width(), self.get_allocated_height()
        radius = self.effective_radius()
        context.save()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        if radius:
            for x, y, start in (
                (width - radius, radius, -math.pi / 2),
                (width - radius, height - radius, 0),
                (radius, height - radius, math.pi / 2),
                (radius, radius, math.pi),
            ):
                context.arc(x, y, radius, start, start + math.pi / 2)
            context.close_path()
        else:
            context.rectangle(0, 0, width, height)
        context.clip()
        style = self.get_style_context()
        Gtk.render_background(style, context, 0, 0, width, height)
        Gtk.render_frame(style, context, 0, 0, width, height)
        result = Gtk.Window.do_draw(self, context)
        context.restore()
        return result

    def update_input_shape(self):
        window = self.get_window()
        if window is None:
            return
        radius = self.effective_radius()
        if not radius:
            window.input_shape_combine_region(None, 0, 0)
            return
        width, height = self.get_allocated_width(), self.get_allocated_height()
        region = cairo.Region()
        for y in range(height):
            distance = max(radius - y - 0.5, y + 0.5 - height + radius, 0)
            inset = math.ceil(radius - math.sqrt(max(0, radius**2 - distance**2)))
            region.union(cairo.RectangleInt(inset, y, max(1, width - 2 * inset), 1))
        window.input_shape_combine_region(region, 0, 0)
