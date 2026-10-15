# Architecture

## Components

- `capture.py` creates one dedicated session-bus connection, calls
  `BecomeMonitor`, and filters notification calls and their replies.
- `protocol.py` converts the eight `Notify` arguments into a small application
  model. It retains `desktop-entry` identity and urgency while dropping
  arbitrary hints and sender metadata. Valid Walite v1 activation hints are the
  only private capability exception, scoped to their notification record.
- `history.py` persists a bounded record set in SQLite. The database is private
  and replacement IDs do not overwrite earlier local rows.
- `dunst.py` runs `dunstctl` only in response to user actions. There is no
  periodic subprocess or polling loop.
- `applications.py` resolves desktop identity or unambiguous application names
  against installed desktop files, respecting user overrides.
- `activation.py` validates Walite's private X11 marker or matches installed
  desktop IDs/`StartupWMClass` against X11 window classes, then raises the sole
  matching window for retained actions.
- `ui.py` owns the XEmbed tray icon and GTK window. Application groups are
  reconstructed from the bounded store when the view changes.
- `walite.py` strictly validates opaque per-notification capabilities and sends
  one bounded request to a private, owner/peer-verified Unix socket. A separate
  Open discussion control atomically claims the stored capability before an
  attempt. V2 consumes it once on the server and returns a fresh, fixed-expiry
  successor; the tray conditionally saves it in the same claimed record so the
  control remains reusable without replay. V1 remains one-shot. Known failures
  do not focus Walite; queue admission precedes best-effort unique-marker focus.
  [Security, ordering and no-acknowledgment limits](WALITE.md) are explicit.
- `tray_icon.py` caches an in-memory, theme-colored clean bell with one optional
  white unread dot. DND never selects a different bell image.
- `settings.py` edits draft appearance preferences. `config.py` bounds values,
  fits panel geometry, and atomically saves only appearance options.
- `panel.py` clips background and children to rounded compositor-backed X11
  surfaces; without a compositor it uses an opaque rectangular surface.

## Event path

```text
application
    │ Notify call
    ▼
session D-Bus ───────────────► Dunst ─────► top-right popup
    │ monitor copy                │
    ▼                             └────────► numeric notification ID
dunst-tray capture ─► SQLite ─► grouped GTK notification center
```

`dunst-tray` never becomes a proxy and never owns the notification service.
Consequently, exiting or crashing it does not interrupt Dunst.

## Replacements and stack tags

The local store inserts every observed call. `replaces_id`, duplicate content,
and Dunst stack tags are retained as context but never treated as instructions
to overwrite an older local row. This is what preserves twenty distinct Walite
messages even if Dunst displays a single replacing popup.

## Actions

The monitor correlates a `Notify` call's sender/serial pair with the method
reply's destination/reply-serial pair and records the returned Dunst ID. Dunst
1.12.2 nevertheless invokes actions by visible stack position, not by ID. The
center does not offer unverified position-based callbacks. **Show app** means
verified application focus, never selection of a specific message. Availability
is cached per application for each panel rebuild; missing, unknown, or ambiguous
targets are disabled with explanations. Clicks revalidate the target.

Installed desktop applications such as ChatGPT use durable window activation.
The notification's `desktop-entry` hint, or an unambiguous display name for
older records, resolves the application's icon and expected X11 classes.
`WM_CLASS` is inspected per top-level window, avoiding title matching and
preserving spaces in Electron resource names. Activation requires one matching
window and reports a visible error otherwise. No desktop-file command or
notification text is executed. This activates the application without claiming
to restore a notification's private navigation callback. A schema migration
adds `desktop_entry` to existing SQLite stores without removing retained rows.

Walite exposes a durable application-level fallback: its running X11 window has
a randomized `_WALITE_NOTIFICATION_<token>` property whose string value repeats
the same token. `activation.py` enumerates top-level windows, validates this
name/value pair strictly, requires exactly one match, and raises it by numeric
window ID. This makes every retained Walite **Show app** control useful without
executing saved notification text or guessing by window title. The historical
record does not contain Walite's private chat identifier, so this fallback
raises the application but does not claim to select the original chat.

## Failure isolation

- If monitoring is denied, the tray and Dunst controls remain available.
- If Dunst is temporarily absent, saved history remains readable and controls
  report an error rather than starting another daemon.
- SQLite retention runs in the same transaction as each insert.
- A single-instance file lock prevents duplicate local history capture.

## Unread and appearance

The SQLite unread flag defaults true for new captures. Existing pre-unread
history migrates as read. Opening the center acknowledges the retained snapshot;
new arrivals while open stay unread until the next explicit opening. Closing,
DND changes, and appearance edits do not acknowledge anything. Retention and
clearing naturally remove associated unread flags.

Hidden-center arrivals only update the in-memory bell/tooltip. Visible bursts
coalesce into one event-driven panel rebuild, preserving expansion, paging, and
scroll position. There is no polling or continually generated icon file.

Appearance Apply validates and atomically replaces config.ini with mode 0600,
preserving unrelated options. Cancel and Restore Defaults do not save. The CSS
provider updates in place; the rounded window clips child drawing and input
corners, and geometry responds to monitor/work-area changes.

