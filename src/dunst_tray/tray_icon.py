"""A clean, theme-colored bell and one optional white unread dot."""

from __future__ import annotations

import math
from functools import lru_cache

import cairo
import gi

gi.require_version("Gdk", "3.0")
gi.require_foreign("cairo")
from gi.repository import Gdk  # noqa: E402


@lru_cache(maxsize=48)
def render_bell(size: int, unread: bool, color: tuple[float, float, float]):
    """Render in memory only, cached by tray size, theme color and read state."""
    size = max(12, min(64, size))
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    context = cairo.Context(surface)
    context.scale(size / 24, size / 24)
    context.set_line_cap(cairo.LINE_CAP_ROUND)
    context.set_line_join(cairo.LINE_JOIN_ROUND)
    context.move_to(6, 15)
    context.line_to(6, 10)
    context.curve_to(6, 3, 18, 3, 18, 10)
    context.line_to(18, 15)
    context.line_to(20, 18)
    context.line_to(4, 18)
    context.close_path()
    context.move_to(10, 21)
    context.curve_to(11, 22, 13, 22, 14, 21)
    # A thin contrasting edge keeps the theme foreground visible on panels
    # whose light/dark preference differs from the application's GTK theme.
    contrast = 0.05 if sum(color) > 1.5 else 0.95
    context.set_source_rgba(contrast, contrast, contrast, 0.8)
    context.set_line_width(3)
    context.stroke_preserve()
    context.set_source_rgb(*color)
    context.set_line_width(1.65)
    context.stroke()
    if unread:
        context.arc(19.3, 4.7, 2.5, 0, 2 * math.pi)
        context.set_source_rgba(0.08, 0.08, 0.08, 0.95)
        context.set_line_width(1.4)
        context.stroke_preserve()
        context.set_source_rgb(1, 1, 1)
        context.fill()
    surface.flush()
    return Gdk.pixbuf_get_from_surface(surface, 0, 0, size, size)
