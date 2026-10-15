# Walite discussion navigation

Compatible producer: Walite `fix/notification-chat-navigation`, commit
`77459fd35542c42fb8422b0e5e700506e7e38109`. The originating contract is
Walite's `docs/dunst-tray-integration.md` (MIT). This adapter implements the
version 1 `x-walite-activation` string hint independently in Python.

**Show app** remains window focus only. A separate **Open discussion** appears
on valid Walite records, even without a live Dunst default action. Old history
and missing/unknown/malformed hints retain their existing behavior. Direct and
group chats use identical opaque-ticket routing; the tray never receives a
stable ChatID. The private SQLite migration preserves history and unread flags.

## Security and lifetime

- Parse bounded JSON with exact known keys, integer version 1, a lowercase
  64-hex ticket, and Walite's bounded private `/tmp/walite-activation-…/s-….sock`
  namespace. Reject duplicates, legacy credentials, identities and traversal.
- Open the parent without following symlinks. Require same-user ownership,
  directory mode 0700, native socket type and mode 0600; reject socket symlinks.
  Pin the directory descriptor through Linux `/proc/self/fd`, verify the peer
  UID with `SO_PEERCRED`, and recheck ownership, modes and socket inode after
  connecting, before sending any capability.
- Send one compact UTF-8 JSON object containing only `version` and
  `activation_id`, shut down the write side for EOF framing, and close. The
  bounded synchronous transport timeout is 0.5 seconds. No response is read.
- Capabilities live only in their bounded private notification record. Claim
  and remove the capability atomically before the first attempt, so stale UI
  events cannot replay it. Retention/clear removes it with the record. It is
  excluded from model representations, UI text and diagnostics, and never
  passed to subprocesses. Window focusing receives only a validated X11 ID.
- Availability checks never connect or consume a ticket. Errors are redacted.
  Missing/refused/untrusted endpoints never launch Walite or focus a window.
  Multiple instances are routed only through the record's exact endpoint and
  ticket. No process/window is guessed by title, display name or PID.

The spec requests focus followed by sending, but also requires transport failure
to leave focus unchanged. To honor that failure guarantee, this client validates
and sends **before** its best-effort existing marker-based focus. If there is
not exactly one marked Walite window, it sends to the exact socket without
guessing which window to raise. **Show app** retains its ambiguity protection.

There is intentionally **no delivery acknowledgment**. A successful write is
not proof of selection: Walite retains only the newest 32 tickets, consumes each
once, discards them on exit, and drops navigation while composing/sending/modal
interactions are active. A remotely expired/evicted ticket cannot be detected
by this protocol and can still cause best-effort window focus after a write.
The tray does not claim an expired ticket opened a discussion or retry it.
Guaranteeing unchanged focus for that undetectable case, or exact-instance
window focus among multiple marked terminals, would require a producer-side
protocol extension. No such extension is invented here.

## Tests

`tests/test_walite.py` covers strict parsing, privacy, real Unix sockets/EOF,
ownership/modes/types/symlinks, peer mismatch, inode replacement, missing/refused
endpoints, redacted errors, migration/restart, one-attempt claims and retention.
GTK integration covers both independent controls, successful request routing,
failed-request focus isolation, records without live actions and 280px layout.
The normal history, grouping, unread, DND and appearance regression tests remain.

`tests/fixtures/walite_navigation_test.go` is an opt-in real-terminal fixture,
adapted from Walite's `cmd/walite/linux_notification_manual_test.go`, symbol
`TestLinuxNotificationManualFixture` (MIT, copyright 2026 Antoine Baudrimont).
Only the harness is adapted: it binds the production ticket receiver, creates
synthetic direct/group chats, and records content-free rendered-state labels.
It constructs no WhatsApp client, account, service or database. Production
notification metadata, receiver and TUI implementations remain unmodified.

To reproduce the manual check:

1. Stop the normal tray and Walite gracefully; retain their settings/data.
2. Archive the exact Walite commit into a new private temporary source folder.
   Copy the fixture into its `cmd/walite/dunst_tray_navigation_test.go` and run
   `go test -c -o walite-fixture ./cmd/walite` there.
3. Create another private temporary directory (0700). In a real X11 terminal,
   set `WALITE_TRAY_TEST_DIR` to it and execute the fixture binary with
   `-test.run=^TestDunstTrayNavigationFixture$ -test.timeout=10m`.
4. With the installed tray package on `PYTHONPATH`, execute
   `python3 scripts/check_walite_live.py FIXTURE_DIRECTORY NUMERIC_WINDOW_ID`.
   This physically clicks the real GTK buttons and checks the real rendered
   TUI plus `_NET_ACTIVE_WINDOW`, not merely successful socket writes. The
   temporary history filters out personal notifications. Synthetic popups are
   transient; DND and daemon history are not changed/cleared.
5. The check stops the fixture, checks disabled navigation, and closes its
   temporary tray. Restore the normal applications and original desktop focus.

It tests an older group notification, a newer direct notification, generic
focus without ticket consumption, draft/modal protection, unavailable receiver,
history preservation and minimum-width controls. It does not select a private
real-account conversation or send a message. See `VALIDATION.md` for results,
not assumptions about whether this opt-in check was run.
