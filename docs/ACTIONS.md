# Application actions

## Generic window focus

The sender's default callback is **not** a prerequisite for Show app. Earlier
versions incorrectly gated the renderer and both activation checks on it;
aerc's notify-send hook supplied no callback, so it displayed neither control.
Every retained record now offers Show app, disabled with a reason if unsafe.

Resolution uses the following conservative identities, with click-time
revalidation and exactly one matching top-level window required:

1. `desktop-entry` resolves an installed desktop file, respecting XDG user
   overrides. Otherwise an exact, unambiguous app name/desktop ID is used.
   An ambiguous name or unresolved explicit desktop entry never falls through
   to a weaker identity.
2. Desktop ID/`StartupWMClass` matches either exact X11 `WM_CLASS` field.
   Without a desktop file, only the exact notification application name may
   match WM_CLASS; titles and message text are never searched.
3. For desktop entries declaring `Terminal=true`, an unmatched class can use
   the desktop command's executable **identity**, never execute its command.
   `_NET_WM_PID` must belong to this user and `WM_CLIENT_MACHINE` must identify
   the local host. Bounded numeric `/proc` ancestry must identify exactly one
   foreground PTY process-group leader, whose executable basename matches.
   Shell/interpreter/launcher executable identities are excluded. No process
   arguments, email subjects, terminal titles or message contents are read.

Unreadable ownership, background processes, multiple matching windows, shared
terminal servers with multiple PTYs, tmux/nested-session ambiguity and foreign
hosts fail closed. Terminal wrappers without a stable class/direct executable
may remain unavailable. This is not a promise to identify every terminal app.
X11 properties/desktop files are same-session identities, not a security
boundary against a malicious application already controlling that X11 session.

Show app restores/raises via numeric window ID. It never starts an application
or invokes a desktop Exec line. Walite keeps its stricter randomized X11 marker
for generic focusing and its existing socket protocol for navigation.

## Message-level navigation

The [notification specification](https://specifications.freedesktop.org/notification/latest-single/)
defines opaque action keys, not universal executable commands or message URIs.
The companion retains those keys, desktop identity and the returned Dunst ID,
but arbitrary hints are deliberately dropped. Notification text never becomes
a command or a guessed deep link.

In [Dunst 1.12.2](https://github.com/dunst-project/dunst/blob/v1.12.2/src/dbus.c),
the public action control selects a **displayed position**, not a retained
notification ID. Replaying that position for history can activate a different
notification. Forging an ActionInvoked signal is not a supported replacement.
Therefore an ordinary stored callback is shown as disabled Open message with
an explanation; absent interfaces do not create a navigation button. No current
generic URI hint or documented ID-addressed Dunst action is available here.
A future adapter requires an explicit validated producer-to-item contract, not
arbitrary URI/command execution from notification metadata.

The supported message adapter remains [Walite v2](WALITE.md): one-use ticket
rotation, fixed expiry, verified Unix sockets, no ChatIDs, draft/modal protection
and no automatic sending. Its capture, client, history and wire protocol are
unchanged by this generic-focus work.

## aerc

Inspected the installed aerc help/manual and notification-hook declaration,
without reading account data, mail or credentials. Its current hook calls
notify-send without an action, desktop-entry hint or message identifier.
The desktop launcher declares a stable `StartupWMClass=aerc`, matching the
existing terminal window; this makes generic Show app reliable without an
aerc-specific code branch.

aerc **does** support command IPC to a running instance, and its mail-received
hook can expose account/folder/message-ID metadata. See the upstream
[command manual](https://github.com/rjarry/aerc/blob/master/doc/aerc.1.scd) and
[hook configuration](https://github.com/rjarry/aerc/blob/master/doc/aerc-config.5.scd).
However, the current notification does not bind those fields to a retained
record. A received email cannot safely be selected from its subject/body, and
`mailto:` opens composition rather than the associated received message.

Consequently **opening a specific aerc email is not implemented or claimed**.
It would need a coordinated hook/receiver contract, authenticated opaque target
metadata and explicit protection of compose/modal state. This task changes no
aerc configuration, launches no extra client and sends no email.

## Inactivity behavior

`[panel] auto_hide=false`, `auto_hide_timeout=5` keep backward-compatible manual
closing. Settings bounds the timeout to 3–120 seconds and saves it atomically
alongside existing preferences. Cancel/Defaults remain draft-only until Apply.

One monotonic deadline and at most one one-shot GLib source are active while
visible/enabled. Activity updates the deadline without allocating a new source
per event; if necessary, expiry schedules the remaining delay once. Hidden,
disabled or held states have no timer. There is no polling thread.
Dynamic GTK children are watched for motion, click/release, scroll, key and
touch events. Pointer holds, menus, Settings and nested action/modal transactions
cancel the pending source; release starts a full interval. Hiding cancels the
source and changes only window visibility, not history/read state/DND/tray.
