# dunst_tray

A lightweight system-tray bell and persistent notification center for **Dunst
on Linux/X11**.

Keep Dunst's popups and add a place to review notifications later. `dunst_tray`
passively observes notification calls, stores a bounded local history, and
groups messages by application. Dunst remains the sole notification daemon.

Built with Python, GTK3, and SQLite, with event-driven updates and no polling
loop, web server, or browser runtime.

**Status:** pre-release (`0.1.0.dev0`). Verified on MX Linux / Debian Trixie with
Xfce, X11, and Dunst 1.12.2. i3 support is intended but not yet verified.

## Features

- Persistent tray bell with **one white dot** when retained notifications are
  unread. No badge count or exclamation mark.
- Notification history and unread state survive application restarts.
- A notification center with per-application groups, expand/collapse, scrolling,
  and incremental access to older messages.
- Independent retention of notification calls, including messages that Dunst
  replaces or combines into a single popup. Default retention: 100 messages.
- Do Not Disturb controls, replay through Dunst, and confirmed history clearing.
- **Show app** focuses a verified running application window. Tested with
  ChatGPT, Walite, and Xfce Task Manager.
- **Open discussion** uses compatible Walite notifications' private one-time
  tickets to request the original direct/group chat, independently of Show app.
- Application icons from notification data, icon themes, or installed desktop
  entries, with a fallback when an icon is unavailable.
- Graphical appearance settings for background opacity, width, height, corner
  radius, and application-icon visibility.
- **Apply**, **Cancel**, and **Restore Defaults**, with saved preferences and
  immediate appearance updates.

## Screenshots

Screenshots are not included in this public snapshot. Desktop validation used
synthetic notifications; personal notification contents are not included in
the repository. Any future screenshots should also use synthetic content.

## Requirements

- Linux with **X11**, Python **3.11+**, GTK3, PyGObject, and Pycairo.
- A running **Dunst** instance, including its `dunstctl` command.
- `wmctrl` and `xprop` for verified application-window focusing.
- A session D-Bus that permits same-user notification monitoring through
  `org.freedesktop.DBus.Monitoring.BecomeMonitor`.
- An **XEmbed system tray**, such as Xfce's Notification Area. i3 needs an
  XEmbed-capable tray configuration; its integration remains unverified.
- An X11 compositor for translucent backgrounds and rounded clipping. Without
  one, the center uses an opaque rectangular surface.

SQLite is provided by Python's standard library. Wayland is not supported.

## Installation

Install system dependencies on Debian / MX Linux:

```sh
sudo apt install git dunst python3 python3-gi python3-cairo \
  python3-gi-cairo gir1.2-gtk-3.0 wmctrl x11-utils
```

Clone and install as your normal user:

```sh
git clone https://github.com/antoinebaudrimont-beep/dunst_tray.git
cd dunst_tray
./scripts/install.sh
~/.local/bin/dunst-tray
```

The installer needs no root privileges. It installs the application and creates
a desktop autostart entry for the current user. It preserves existing config
and history and does not edit, start, stop, or replace Dunst. Keep your existing
Dunst session setup running.

| Default location | Purpose |
| --- | --- |
| `~/.local/opt/dunst-tray/` | Application files |
| `~/.local/bin/dunst-tray` | Launcher |
| `~/.config/dunst-tray/config.ini` | Preferences |
| `~/.local/share/dunst-tray/history.sqlite3` | Private notification history |
| `~/.config/autostart/dunst-tray.desktop` | Desktop autostart entry |

Config, data, and autostart paths honor `XDG_CONFIG_HOME` / `XDG_DATA_HOME` when
set. The launcher and application directory stay under `~/.local`.

Autostart is configured by installation, but a real logout/login or reboot
cycle has **not yet been verified**. A single-instance lock prevents duplicate
tray processes. To update, quit the running tray, pull changes, rerun the
installer, and start the launcher again.

## Usage

- **Left-click the bell:** open or close the notification center.
- **Right-click the bell:** open controls for notifications, replay, history,
  Settings, and quitting the tray application.
- **Notifications enabled:** uncheck to enable DND; check to resume Dunst.
  Notifications captured during DND still count as unread.
- **Application group header:** expand or collapse its messages. Messages are
  newest first; **Show older** reveals more without deleting retained text.
- **Show app:** raise the running application's window. This does not open a
  particular message or start another application process.
- **Open discussion (Walite):** request that notification's original chat in
  the already-running producer. Tickets expire; busy Walite protects drafts
  and dialogs. See the [integration and limitations](docs/WALITE.md).
- **Clear notification history:** after confirmation, clear the companion's
  retained history and Dunst's history. This resets unread state.

### Unread behavior

Opening the center acknowledges all currently retained messages and removes
the dot. Messages arriving while the center is open remain unread until the
next explicit opening. Closing alone does not acknowledge them. Unread state
persists across tray restarts and is independent of DND and total history size.
Existing history from before the unread feature migrates as read.

### Appearance settings

Open **Settings** from the tray menu:

| Setting | Range |
| --- | --- |
| Background opacity | 50–100% |
| Width | 280–550 px |
| Height | 300–850 px |
| Corner radius | 0–24 px |
| Show application icons | On / off; disabling reclaims icon spacing |

The panel fits the monitor's usable work area. Opacity affects the background
while text stays readable. These controls affect the notification center, not
Dunst's popups.

**Apply** saves and repaints immediately. **Cancel** discards unsaved edits;
changes already applied remain saved. **Restore Defaults** fills the controls
and takes effect only after Apply. Appearance changes do not clear history or
require a Dunst restart.

### Configuration file

Default preferences:

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

Restart the tray after manual file edits. The appearance dialog saves its
options atomically while preserving unrelated settings.

## Compatibility and limitations

Verified desktop behavior includes notification capture, Xfce tray interaction,
DND, history/unread persistence, appearance persistence, and window focusing
for ChatGPT, Walite, and Task Manager. Details and actual evidence are in the
[validation record](docs/VALIDATION.md).

- **Show app is application focus, not message navigation.** It appears for
  notifications advertising a default action and is enabled only for a reliable
  single running window. Missing, unknown, or ambiguous targets are disabled
  with an explanatory tooltip. No window is selected using partial title text.
- Dunst's original actions are tied to popup position and sender lifetime;
  saved callbacks cannot safely select a particular historical message. New
  Walite notifications use a separate documented one-time ticket protocol;
  older records retain application focus through the existing X11 marker.
- D-Bus policy restrictions can prevent passive capture while leaving tray
  controls usable. The tray never takes ownership of the notification service.
- Popups, popup stacking, screen position, and visible-popup limits remain
  Dunst's responsibility. A reference configuration fragment is provided in
  [docs/dunst-integration.conf](docs/dunst-integration.conf).
- Reboot/login behavior, i3 integration, and **real aerc notifications** are
  unverified. The aerc scenario was tested using synthetic fixtures only.
- Actual light-panel configuration, compositor-off operation, monitor hotplug,
  session-bus disconnection, and long-duration resource use remain unverified.

## Testing

The Walite integration check on **2026-10-15** ran all **50 tests successfully**:
39 non-GUI tests and 11 opt-in GTK/X11 tests, including native Unix sockets.

Run pure tests without a desktop session:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

This discovers 50 tests, runs 39, and skips the 11 GTK checks. Run all 50 on an
X11 desktop with the system GTK/Python dependencies installed:

```sh
DUNST_TRAY_GUI_TESTS=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
sh -n scripts/install.sh scripts/uninstall.sh
```

`desktop-file-validate assets/dunst-tray.desktop` is an additional check when
`desktop-file-utils` is installed.

Automated tests are separate from the recorded **live Xfce acceptance** of real
capture, tray clicks, DND, 20-message unread behavior, settings, restarts, and
application focus. That acceptance was completed before this documentation
publication pass and is not claimed as a fresh live run here.

[`scripts/check_live.py`](scripts/check_live.py) contains the opt-in live
sequence. Read its header before running: it briefly changes/restores DND and
requires stopping the normal tray to keep fixtures out of normal history. It
uses temporary synthetic history, filters personal notifications, and disables
daemon-history deletion. Restart the normal tray afterward.

## Privacy

Notification contents stay in the local SQLite store. Its directory is mode
`0700` and the database is mode `0600`. Display fields, action identifiers,
desktop identity, and read state are retained; arbitrary hints and sender PIDs
are not. The known Walite activation hint is retained privately with its record
until its first attempt, retention or clearing; it contains no stable ChatID.
Do not attach private history or real message screenshots to issues.

## Uninstall

Quit the tray and remove the application and autostart entry while keeping
preferences and history:

```sh
./scripts/uninstall.sh
```

To also permanently remove preferences and notification history:

```sh
./scripts/uninstall.sh --purge
```

Dunst is not removed or reconfigured.

## Development

See the [architecture](docs/ARCHITECTURE.md),
[work checkpoint](docs/WORK_PROGRESS.md), and
[publishing notes](docs/PUBLISHING.md). Use synthetic fixtures and screenshots,
run relevant tests, and keep changes focused.

## License

[MIT](LICENSE). The existing license is preserved.
