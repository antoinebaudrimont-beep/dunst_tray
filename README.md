# dunst-tray

`dunst-tray` is a lightweight GTK3 system-tray bell and grouped notification
center for Dunst on X11. Dunst remains the only notification daemon and keeps
rendering popups; this companion passively observes notification calls and
retains a separate, bounded history.

The initial target is MX Linux 25.x / Debian 13 (Trixie), Xfce, and i3 on X11.
It uses Python, PyGObject, SQLite from the standard library, and no polling loop,
web server, browser runtime, or second notification daemon.

> Screenshot placeholder: add a sanitized notification-center image before a
> public release. Never use real notification text in project screenshots.

## Status

This repository is pre-release (`0.1.0.dev0`). The backend, tray, grouped
history, Dunst controls, installer, and automated tests are functional. Xfce
live integration has been tested on the target machine. i3 and interactive
mouse behavior still need a manual desktop pass; see
[`docs/VALIDATION.md`](docs/VALIDATION.md).

## Features

- Persistent `Gtk.StatusIcon` bell for XEmbed-compatible Xfce/i3 trays.
- A single white dot indicates unread retained notifications and survives tray
  restarts; Do Not Disturb does not change the bell or unread state.
- Left click opens or hides a compact top-right notification center.
- Right-click menu for Do Not Disturb, opening the center, replaying the latest
  Dunst notification, clearing history, appearance settings, and quitting.
- Notifications grouped by application without deleting collapsed messages.
- Five messages shown initially per expanded group; “Show older” reveals more.
- Configurable retention of 100 notifications by default.
- Private SQLite persistence across tray and Dunst restarts.
- Application icons resolved from notification data or installed desktop
  entries, with a safe symbolic fallback.
- Graphical panel appearance settings for opacity, size, corners, and icons.
- Durable **Show app** controls for every retained Walite notification, using
  Walite's own X11 window marker to raise the running application.
- Durable application activation for installed desktop applications such as
  ChatGPT, including retained notifications whose popup has expired.
- Event-driven D-Bus capture and zero measured CPU use while idle in a
  three-second sample on the target machine.

## Dependencies

Install repository packages on Debian/MX Linux:

```sh
sudo apt install dunst python3 python3-gi python3-cairo python3-gi-cairo gir1.2-gtk-3.0 wmctrl x11-utils
```

`dunstctl` is included with Dunst. `notify-send` from `libnotify-bin` is useful
for manual testing but is not required at runtime.

Required runtime conditions:

- An X11 session.
- A running Dunst notification daemon.
- A session D-Bus that permits the same user to call
  `org.freedesktop.DBus.Monitoring.BecomeMonitor`.
- An XEmbed system tray. Xfce's Notification Area works; i3 needs a configured
  `bar { tray_output ... }` or another compatible tray.

## Install

The installer only writes inside the current user's home directory. It does not
edit, stop, disable, or replace Dunst.

```sh
git clone /path/to/dunst-tray
cd dunst-tray
./scripts/install.sh
~/.local/bin/dunst-tray
```

Installed layout:

```text
~/.local/opt/dunst-tray/             application files
~/.local/bin/dunst-tray              launcher
~/.config/dunst-tray/config.ini      user configuration
~/.local/share/dunst-tray/           private history database
~/.config/autostart/dunst-tray.desktop
```

Log out and back in to exercise autostart, or launch the command directly. A
single-instance lock prevents accidental duplicate monitors.

## Configuration

The default `~/.config/dunst-tray/config.ini` is:

```ini
[history]
limit = 100
page_size = 5

[panel]
width = 380
height = 680
opacity = 97
corner_radius = 14
show_icons = true
margin_top = 48
margin_right = 16

[capture]
monitor_dbus = true
```

Use **Settings** in the tray menu to change appearance immediately. The dialog
offers opacity 50–100%, width 280–550 px, height 300–850 px, corner radius
0–24 px, and application-icon visibility. **Apply** saves and repaints;
**Cancel** discards edits since the last Apply. **Restore Defaults** fills the
controls without saving until Apply. Size is fitted to the monitor work area.
Opacity affects the background, keeping text readable; opacity and rounded
clipping require an X11 compositor. Without one the panel is opaque and square.
Restart the tray only after manually editing the configuration file.
The database directory is mode `0700` and the database is mode `0600`. Only
display-relevant fields, action identifiers, and the `desktop-entry` application
identity are saved; sender PID and arbitrary D-Bus hints are not persisted.

## Controls

- **Left click bell:** show or hide the notification center.
- **Right click bell:** open the control menu.
- **Notifications enabled:** uncheck to pause Dunst (Do Not Disturb); check to
  resume.
- **Replay latest:** ask Dunst to pop its latest history entry.
- **Clear notification history:** after confirmation, clear both the local
  companion history and Dunst's current history.
- **Show app (Walite):** raise the currently running, X11-marked Walite window from
  any retained Walite entry.
- **Show app (installed desktop applications):** raise the running window identified
  by its desktop ID or `StartupWMClass`. This includes ChatGPT and works for
  older retained entries without a live Dunst callback.
- **Unresolved or ambiguous targets:** the control is disabled and its tooltip
  explains why. Application focus does not select the original message. The
  center never invokes an unrelated popup's position-based Dunst callback and
  never launches another application process.

Messages inside each application group are newest first. The complete original
summary and body strings remain stored even while the group is collapsed.

Opening the center acknowledges all currently retained messages. New messages
received while it is open remain unread until the next explicit opening;
closing alone does not acknowledge them. Clearing history resets unread state.
Existing history migrates as read on upgrade; new captures start unread.

## How capture works

The application opens a dedicated, monitor-only session-bus connection and
observes `org.freedesktop.Notifications.Notify` method calls. It never requests
or owns `org.freedesktop.Notifications`; Dunst remains the sole service owner.
Each call is stored before Dunst applies popup replacement, duplicate stacking,
or the Walite stack tag. Method replies are observed to retain Dunst's numeric
ID for correlation, but Dunst actions are position-based rather than ID-based.

The monitor filter consumes its private copy rather than passing it to Gio's
normal dispatcher. This follows Gio's filter contract and prevents the monitor
from generating a false method error. See the
[Gio `DBusConnection.add_filter` documentation](https://docs.gtk.org/gio/method.DBusConnection.add_filter.html)
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Dunst integration and popup limits

The existing Dunst configuration does not need to change when it already has a
top-right origin, bounded width/height, rounded corners, icons, and a small
`notification_limit`. A reference fragment is in
[`docs/dunst-integration.conf`](docs/dunst-integration.conf).

Dunst 1.12.2 can limit the number displayed and indicate hidden notifications.
It can stack duplicates and apply a fixed stack tag, as used for Walite. It does
not provide the requested dynamic policy “show one through five individually,
then replace them with an expandable sixth popup.” The reliable approximation
is:

1. Dunst shows at most the configured number of top-right cards.
2. `indicate_hidden = yes` indicates overflow.
3. Walite's stack tag prevents its popups from flooding the screen.
4. `dunst-tray` independently retains every observed call for grouped browsing.

Do not remove Walite's stack tag merely to populate Dunst history. The
companion history is captured before that rule is applied.

## Actions and privacy limitations

- Walite is handled specially. Every retained Walite **Show app** control locates
  the sole window carrying Walite's private X11 marker and raises it with
  `wmctrl`. This remains usable after the original Dunst callback expires. A
  saved notification cannot reproduce Walite's original per-chat callback, so
  historical entries raise Walite without promising exact chat selection.
- Installed application identity also provides a durable fallback for ChatGPT
  and other desktop apps. The tray checks X11 application classes rather than
  window titles and requires exactly one matching running window. It raises
  the application; it does not recreate a notification's private navigation
  callback or launch an application that has exited. Empty or unavailable
  notification icons fall back to the installed application's icon, honoring
  user desktop-file overrides.
- Original notification actions are D-Bus callbacks, not durable commands.
  Dunst 1.12.2 addresses them by popup position rather than retained ID. The
  center therefore offers verified application focusing, labeled **Show app**,
  rather than replaying callbacks that might now refer to another notification.
  Unknown, missing, and ambiguous window targets are disabled with a tooltip.
- Passive monitoring can see notification content from all applications in the
  user's session. Keep the database private and use Clear or uninstall
  `--purge` when appropriate.
- Desktop environments with restrictive D-Bus monitoring policy will leave the
  tray controls working but disable independent capture; the error is logged to
  stderr.
- `Gtk.StatusIcon` is intentionally used for low-overhead X11/XEmbed support. It
  is not a Wayland status-notifier implementation.
- Rounded panel corners depend on an active X11 compositor.
- The appearance dialog atomically saves only panel preferences and preserves
  unrelated settings. It does not alter Dunst popups or clear notification text.

## Run tests

Pure automated tests do not require a graphical session:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
desktop-file-validate assets/dunst-tray.desktop
```

Opt-in GTK checks on an X11 desktop (temporary synthetic history):

```sh
DUNST_TRAY_GUI_TESTS=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`scripts/check_live.py` provides the recorded real-Xfce acceptance sequence.
Read its header before running: stop the normal tray first, and restart it
afterward. It briefly changes/restores DND, filters out personal notifications,
uses transient synthetic calls, and disables daemon-history deletion.

Manual notification examples must use synthetic content:

```sh
notify-send -a 'Synthetic App' 'Example title' 'Example body'
for n in 1 2 3 4 5; do
  notify-send -a 'Synthetic Batch' "Message $n" "Synthetic body $n"
done
```

The exact executed and outstanding test matrix is documented in
[`docs/VALIDATION.md`](docs/VALIDATION.md). Tests are never claimed there unless
they were actually run.

## Troubleshooting

**No tray icon:** ensure the Xfce Notification Area plugin is present, or enable
an i3 XEmbed tray. Check that another copy is not already running.

**No saved history:** run with `--debug` from a terminal and look for a
`BecomeMonitor` policy error. Dunst history is not used as a fallback because
stack tags and replacement can omit the individual calls this project needs.

**Do Not Disturb is disabled in the menu:** verify `dunstctl is-paused` works in
the same desktop session.

**Icons are missing:** applications should send an absolute readable image path
or an icon name available in the current theme. The center falls back safely.

**Walite Open reports an error:** ensure Walite is running under X11 and that
`wmctrl` and `xprop` are installed. The safety check requires exactly one
Walite-marked window.

**Application Open reports an error:** ensure the application is running and its
desktop file's ID or `StartupWMClass` matches its X11 class. Ambiguous windows
produce a visible error. Restart the tray after installing new desktop entries.

Reopen the center to refresh a disabled target after starting or closing an
application window. Target availability is event-driven rather than polled.

## Uninstall and rollback

Remove the app and autostart entry while preserving settings and history:

```sh
./scripts/uninstall.sh
```

Also permanently remove the private notification database and configuration:

```sh
./scripts/uninstall.sh --purge
```

No Dunst rollback is normally required because installation does not edit the
Dunst configuration. If the reference fragment was merged manually, restore
the backup you created before that manual edit and run `dunstctl reload`.

## Contributing

Use synthetic notifications in tests, bug reports, logs, and screenshots.
Never commit a history database. Run the test commands above, keep backend logic
separate from GTK code, and use Conventional Commit messages.

## License

Licensed under the MIT License. See [`LICENSE`](LICENSE).

## Future publication

The repository is local-only. No GitHub repository, remote, release, or tag is
created. After the remaining manual checks pass, publication can use the
commands in [`docs/PUBLISHING.md`](docs/PUBLISHING.md).

