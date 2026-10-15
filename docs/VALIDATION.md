# Validation record

Date: 2026-10-15  
Target: Debian 13.7 (Trixie), kernel 6.12.111, X11, Xfce, Dunst 1.12.2

## Walite ticket integration — current task

Implemented and locally installed from tray commit `6a62761`; the follow-up
validation commit changes only the opt-in harness and documentation. No push,
tag or release was performed.

- All **50 tray tests pass**, both against the source checkout and against the
  installed package: 39 non-GUI tests (including real Unix sockets) and 11 GTK
  checks. Existing history/grouping/unread/DND/settings tests remain unchanged
  except for the targeted new navigation coverage. Compileall, shell syntax,
  Go fixture formatting and diff whitespace checks pass. Existing deprecated
  GTK StatusIcon warnings remain; there were no test failures in the final run.
- Walite's exact supplied commit `77459fd35542c42fb8422b0e5e700506e7e38109`
  passed `go vet ./...`, `go test ./...` and `go test -race ./...`.
  Its source checkout remains clean on `fix/notification-chat-navigation`.
- Tray installed with the existing `scripts/install.sh` into
  `~/.local/opt/dunst-tray`; source and installed activation module match.
  Settings hash is unchanged; normal history received the additive migration.
- Walite rebuilt with the existing Linux release build flags, without running
  release/publishing tooling, as `v1.2.1-local.77459fd`. Executable, official PNG,
  README and MIT license installed together in a new versioned directory below
  `~/.local/opt/walite`; the existing launcher symlink was repointed only after
  clean shutdown and copied `--version`/`--help`/byte verification. The old
  `v1.2.1` installation remains intact for rollback. Executable SHA-256:
  `be37c2ba9fb50ff02137513ba3fe2a2dde5dcd608616ee599d838912197c33df`.
- Both normal applications were gracefully restarted and the running Walite
  executable was verified to be the new build. They were briefly stopped again
  for the isolated acceptance run, then restored in the original terminal.
  Final processes were live; Walite's validated window marker resolved uniquely.
  DND remained level 0. No session/cache/configuration data was reset or paired.

### Actual X11 navigation acceptance

Ran `scripts/check_walite_live.py` using the **installed tray package**, a
temporary filtered history and a real X11 terminal running the production Walite
notification sender, ticket receiver and TUI from the supplied commit. Only an
isolated archived source tree contained the opt-in Go fixture. No WhatsApp
client or database was constructed by the fixture; all chats/content were
synthetic. The harness's widget-coordinate/queued-refresh handling was corrected
and the complete final run exited successfully.

- Physical **Show app** click raised the fixture without selecting a different
  chat or consuming either notification's ticket.
- Physical **Open discussion** click on the **older group** notification
  selected/rendered the group body. The newer direct notification independently
  selected/rendered the direct body. Both also passed `_NET_ACTIVE_WINDOW`
  checks; these are not merely socket-write assertions.
- Both independent controls fit the real panel at its minimum 280px width.
  Notification records remained grouped and retained; explicit panel review
  acknowledged unread flags as before, and successful attempts removed only
  their capability, not notification history.
- A typed, unsent synthetic draft was retained and its original discussion
  remained selected when another discussion was requested. A settings modal
  likewise blocked navigation; closing it retained the original discussion.
- Graceful fixture termination removed its receiver. Its remaining stored
  navigation control became disabled; history remained and DND was unchanged.
- Final read-only inspection found **zero fixture rows in normal tray history**.
  Synthetic popups were transient. The normal tray and updated Walite were
  restored and desktop focus returned to the conversation.

Not claimed: selecting any private real-account chat, sending any WhatsApp
message, exact-instance focus with multiple marked terminals, or proving remote
acceptance/expiry through the intentionally one-way protocol. The latter has no
acknowledgment; see [documented limits](WALITE.md). Reboot/login and i3 remain
outside this task's verified desktop matrix.

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

## Earlier implementation checks (through 47f79f1)

- 22 unit tests passed for configuration parsing/bounds, Dunst controls,
  retention, grouping, duplicate preservation, Dunst-ID updates, clearing,
  protocol parsing, Walite eligibility, strict marker validation, successful
  activation, missing/ambiguous-window rejection, desktop-file user precedence,
  desktop identity hints, migration of existing history, and activation by
  window class rather than title.
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
- Loaded five retained synthetic Walite records and visually confirmed that
  **Open** was enabled on all five, not only the newest record.
- Clicked **Open** on the oldest retained Walite record and confirmed through
  `_NET_ACTIVE_WINDOW` that the marked running Walite window received focus.
- Loaded two synthetic ChatGPT records with empty icon fields and no live Dunst
  callbacks. Verified the installed ChatGPT SVG rendered to a 38×38 image and
  visually inspected the actual logo in the GTK group header.
- Clicked the older synthetic ChatGPT entry's **Open** button through X11 mouse
  automation. Recorded retained ID 1, confirmed the active window changed from
  the test center to the real ChatGPT window, and confirmed the center hid.
- Removed the synthetic UI fixture database and window-only captures after the
  visual pass.

## Not yet manually verified

- Activating each right-click menu item with a human mouse pass. The right-click
  path was triggered without a crash, but individual menu selection was not
  automated.
- Xfce logout/login autostart.
- i3 tray embedding and geometry.
- Behavior when the session bus is deliberately disconnected.
- Long-duration memory stability beyond the bounded functional load test.

These items require further user-session interaction and are not reported as
passing.

## Resumable improvements acceptance — 2026-10-15

Baseline `47f79f1` was inspected and all 22 original tests rerun. Its deployed
UI, resolver, and activation files matched the repository. The existing
ChatGPT/Walite fixes were verified, not reimplemented.

- Full regression: **37 tests passed**, including 29 pure tests and 8 opt-in
  GTK/X11 tests. Default discovery runs the 29 pure checks and skips 8 GTK checks.
- Source compilation, shell syntax, desktop entry validation, and diff
  whitespace checks passed. No runtime database, log, or personal screenshot is
  tracked. Synthetic preview captures were outside the repository.
- GTK checks cover theme/absolute PNG/deleted-path/desktop/fallback icons,
  synthetic future-aerc metadata, clean/dotted bell rendering at 16/22/24/32,
  read/DND/window lifecycle, settings Apply/Cancel/Defaults, atomic persistence,
  icon-spacing reclamation, group expansion/paging, and actual 280×300 geometry.
- A composited GTK surface at opacity 50/radius 24 had transparent corner alpha
  0 and interior background alpha approximately 128; text remained opaque.
- Window-only synthetic previews of settings and the panel were visually
  inspected. Light/dark sample-background bell previews passed visual review.
  The user's actual light-panel configuration was not changed or tested.

Live `scripts/check_live.py` sequence passed on the real Xfce tray and Dunst:

1. XEmbed bell embedded with zero unread, then one real synthetic Notify call
   changed the bell to the dotted variant.
2. Physical X11 bell clicks opened/closed the center. Opening acknowledged the
   retained snapshot; a new arrival while open stayed unread until reopening.
3. Twenty actual Walite Notify calls were independently captured during actual
   DND. Unread count was 20 and the image was identical to the one-message dot.
4. Reconstructing the tray/store restored the unread state.
5. Physical settings Apply/Cancel clicks saved appearance and retained history
   and unread state. Reconstructing again restored width 320, opacity 70 and
   hidden icons.
6. Physical **Show app** clicks raised the actual ChatGPT, Task Manager, and
   Walite windows; `_NET_ACTIVE_WINDOW` confirmed each exact target. The center
   hid after each successful click. This tests focus, not exact-message
   navigation or invocation of a private original callback.
7. Clearing the temporary companion history reset unread and left the bell
   running. **Dunst history deletion was deliberately disabled in the test**;
   no real user history was erased. Synthetic notifications were transient and
   cleanup closed only IDs returned by the test's own Notify calls.
8. Dunst's owner stayed `:1.44`. Original pause level 0 and original focus were
   restored. The installed old tray was stopped during fixture generation,
   then restarted, so it did not capture synthetic test history.

An initial automatic approval rejection flagged potential daemon-history
deletion. The test was changed to make its daemon-clear operation an explicit
no-op and to remove all daemon-history deletion calls before the approved run.

UNVERIFIED: reboot/login autostart, i3 tray/geometry, actual light-Xfce-panel
configuration, live compositor-off rendering, live resolution/monitor hotplug,
session-bus disconnection, long-duration resource behavior, real aerc
notification integration, native private message callbacks, and deletion of real
Dunst history. These were not inferred from fixture success.

## Deployment verification — 2026-10-15 10:26 CEST

Installed the validated payload `851cf9f` and restarted the identified tray
instance. New PID 50439 holds the lock, owns the XEmbed bell, and started passive
capture. Every installed Python file matches source. Config remains identical
to its mode-0600 backup; the autostart entry remains present. The unread schema
migration succeeded. Only aggregate notification counts were inspected.

Visually checked the actual installed clean bell, then opened the appearance
dialog via its real right-click Settings menu. The dialog belongs to PID 50439
and loads the preserved effective values. Closed without saving. Dunst owner
remains `:1.44`, pause level remains 0, and no Dunst config/history deletion was
performed. Preview scripts/images and startup logs were removed afterward.

