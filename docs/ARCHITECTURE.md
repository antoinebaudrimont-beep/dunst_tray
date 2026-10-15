# Architecture

## Components

- `capture.py` creates one dedicated session-bus connection, calls
  `BecomeMonitor`, and filters notification calls and their replies.
- `protocol.py` converts the eight `Notify` arguments into a small application
  model. It intentionally drops arbitrary hints and sender metadata.
- `history.py` persists a bounded record set in SQLite. The database is private
  and replacement IDs do not overwrite earlier local rows.
- `dunst.py` runs `dunstctl` only in response to user actions. There is no
  periodic subprocess or polling loop.
- `activation.py` validates Walite's private X11 marker and raises the sole
  matching window for retained Walite actions.
- `ui.py` owns the XEmbed tray icon and GTK window. Application groups are
  reconstructed from the bounded store when the view changes.

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
1.12.2 nevertheless invokes actions by visible stack position, not by ID. For
generic applications, the UI therefore enables **Open** only on the newest
notification and invokes position 0. Older actions remain disabled rather than
risk opening the wrong app, and even the newest action becomes invalid when the
popup or sender exits.

Walite exposes a durable application-level fallback: its running X11 window has
a randomized `_WALITE_NOTIFICATION_<token>` property whose string value repeats
the same token. `activation.py` enumerates top-level windows, validates this
name/value pair strictly, requires exactly one match, and raises it by numeric
window ID. This makes every retained Walite **Open** control useful without
executing saved notification text or guessing by window title. The historical
record does not contain Walite's private chat identifier, so this fallback
raises the application but does not claim to select the original chat.

## Failure isolation

- If monitoring is denied, the tray and Dunst controls remain available.
- If Dunst is temporarily absent, saved history remains readable and controls
  report an error rather than starting another daemon.
- SQLite retention runs in the same transaction as each insert.
- A single-instance file lock prevents duplicate local history capture.

