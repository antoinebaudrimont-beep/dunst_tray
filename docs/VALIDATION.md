# Validation record

Date: 2026-10-15  
Target: Debian 13.7 (Trixie), kernel 6.12.111, X11, Xfce, Dunst 1.12.2

## Environment inspection

- Confirmed `DISPLAY=:0.0`, `XDG_SESSION_TYPE=x11`, and Xfce desktop.
- Confirmed `/usr/bin/dunst` is the sole owner of
  `org.freedesktop.Notifications`.
- Confirmed Dunst has X11 support and the Xfce panel is running.
- Confirmed Python 3.13.5, PyGObject, GTK 3.24, Gio, `dunstctl`, `gdbus`,
  `dbus-monitor`, and `notify-send` are installed.
- Inspected the actual user `dunstrc`. It already specifies top-right origin,
  width 360, height up to 140, notification limit 4, hidden indication, rounded
  corners, icons, history length 100, and the Walite stack tag.
- The actual Dunst configuration was not edited.

## Executed automated checks

- 12 unit tests passed for configuration parsing/bounds, Dunst controls,
  retention, grouping, duplicate preservation, Dunst-ID updates, clearing, and
  protocol parsing.
- `compileall` passed for source and tests.
- `dunst-tray --version` returned `0.1.0.dev0`.

## Executed live X11 checks

- Started the GTK tray against a temporary database while Dunst stayed active.
- Verified one notification with an application icon was captured.
- Verified five notifications from one synthetic application were captured.
- Verified twenty synthetic Walite calls were captured independently even with
  the Walite stack tag active.
- Verified multiple applications, different titles/bodies, repeated identical
  messages, and an invalid icon path were captured without a crash.
- Verified every synthetic record in the successful matrix received a Dunst ID.
- Paused and resumed Dunst successfully with `dunstctl`.
- Restarted `dunst.service`; its unique D-Bus owner changed and the already
  running tray captured a post-restart notification.
- Restarted the tray using the same database and confirmed all 37 records then
  present were reloaded. The extra records were notifications that arrived
  naturally during the test, not synthetic fixtures.
- Measured 0.000% CPU over a three-second idle sample, about 72 MiB resident
  memory, and five threads during the debug live run.
- Exited the corrected tray cleanly with SIGINT.
- Deleted both temporary databases immediately after the run because they may
  have contained real notification text. They were outside the repository.
- Confirmed from the installed Dunst 1.12.2 manual and a live negative test that
  `dunstctl action` takes a displayed stack position, not a notification ID.
  The implementation was narrowed accordingly instead of claiming saved-action
  support.
- Invoked position 0 on a live synthetic notification and confirmed its waiting
  sender exited normally.
- Located the 16×16 XEmbed tray window, clicked it through X11 automation, and
  confirmed the center changed from mapped to unmapped on consecutive clicks.
- Confirmed final center geometry of 380×680 at 16 px from the right work-area
  edge and below the top panel.
- Visually inspected a window-only, synthetic-data capture. Confirmed grouped
  application cards, fallback icons, titles/bodies/timestamps, five-message
  expansion, “Show older (3)”, access to all eight records, scrolling, and
  collapse behavior.
- Removed the synthetic UI fixture database and window-only captures after the
  visual pass.

## Not yet manually verified

- Activating each right-click menu item with a human mouse pass. The right-click
  path was triggered without a crash, but individual menu selection was not
  automated.
- Selecting a live notification's **Open** button from the GTK center.
- Xfce logout/login autostart.
- i3 tray embedding and geometry.
- Behavior when the session bus is deliberately disconnected.
- Long-duration memory stability beyond the bounded functional load test.

These items require further user-session interaction and are not reported as
passing. The underlying current-action control was exercised directly, but not
by clicking the GTK button.

