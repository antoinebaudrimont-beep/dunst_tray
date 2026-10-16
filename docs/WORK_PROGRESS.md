# Work progress — resumable implementation

## Current task — universal focus and optional auto-hide (2026-10-16)

- New attached brief authorizes implementation, local installation/restart and
  X11 synthetic acceptance, then commit. **No push or release.** Start clean on
  main at b2c9007 (already tracking the same origin/main). Walite source stays
  unchanged; preserve rotating-ticket v2 and all existing behavior.
- Confirmed root cause: UI, Walite/desktop eligibility and WindowActions all
  incorrectly required a default callback to offer window focus. Installed aerc
  hook has no action, desktop-entry or stable message-ID metadata. Its user
  desktop entry has a precise StartupWMClass; generic Show app can resolve it.
- Installed aerc docs expose command IPC, search/view/account/folder commands,
  and mail-received AERC_MESSAGE_ID, but none of that binds current Notify calls
  to a message. mailto opens a composer, not a received email. Dunst 1.12.2
  introspection confirms callbacks invoke by visible position, not stored ID.
  Never guess from private text, replay arbitrary commands or forge deep links.
- Implement general exact desktop/WM_CLASS identity; conservative terminal
  foreground-process ownership fallback from trusted Terminal/Exec metadata,
  same host/user and single PTY, with no command-line inspection. Ambiguity is
  disabled. Show app is independent of callbacks; unsupported message actions
  remain disabled/hidden with explanations. No application-name patch list.
- Add disabled-by-default auto_hide and 5-second timeout (bounded 3–120) to
  existing settings. Single GLib deadline with activity reset, pointer/menu/
  settings/modal/action holds, clean cancellation on hide/destroy, no polling.
- First old suite had two expected assertions tied to the removed default-action
  gate; update those to the requested new behavior. Add pure identity/timer and
  GTK/settings tests, then full regression and isolated desktop acceptance.
- COMPLETE: 74 tests pass against source and final installed package (57
  headless/native-socket + 17 GTK). Syntax, desktop-file and diff checks pass.
  Added a regression that caught/fixed weak-wrapper tracking and Gtk.Box packing
  bypassing Container::add; rebuilt/paged controls are now watched and pruned.
- Real X11 synthetic acceptance passed against source and installed package:
  aerc restored from minimized, ChatGPT, Task Manager, Walite, plain GTK,
  missing icons, unknown/ambiguous targets, foreground-PTY resolution and two
  matching terminal windows. Final actual aerc focus also passes with no
  desktop-entry hint and no default callback, without creating a history row.
- Auto-hide live: disabled stays open, physical Apply persists, Settings and
  held controls pause, mouse/scroll reset, hiding preserves new unread/history/
  tray, 15 reopen/close cycles cancel sources, preferences reload after restart.
- Fresh offline production-Walite TUI check with normal Walite left running:
  repeated/alternating direct/group notifications navigate with auto-hide on,
  one-use fresh fixed-expiry rotation and retained rows. Ambiguous marker focus
  is rejected; no arbitrary raise. Existing full security tests pass unchanged.
- Existing installer deployed final source; normal tray restored, instance lock
  verified, config hash unchanged, normal history aggregates unchanged/zero
  fixture rows, private modes 0700/0600, DND 0 and same Dunst owner. Auto-hide
  remains off in the user's existing preferences. Code-only rollback retained
  in pre-actions-autohide-20261016. Disposable synthetic build/run tree removed.
- Walite source untouched/clean on main at cc694de (merge containing 5ad0b96).
  No Walite/aerc/Dunst/account changes or normal Walite restart. Full results,
  limits and exact file map are in VALIDATION.md and ACTIONS.md.
- Implementation, deployment and validation complete; record in one local
  commit only. **No push, tag or release**.

## Current task — repeatable Walite navigation (2026-10-15)

- User confirms real WhatsApp navigation and Xfce reboot autostart work.
  New requirement: keep Open discussion usable repeatedly without replaying
  consumed tickets. No push/release. Both repositories start clean.
- Coordinated design: version 2 hints/requests, server-side atomic one-use
  ticket rotation returning a fresh capability for the same private ChatID.
  Keep bounded 32 notification chains, original FIFO position, absolute 24-hour
  expiry (not extended on clicks), private socket verification, v1 compatibility,
  draft/modal protection, and unchanged generic focus. No automatic retries.
- Response acknowledges bounded queue admission only, not rendered selection.
  Expired/evicted/unknown tickets return a redacted unavailable result; transport
  ambiguity fails closed. No fallback to stable identities or reusable tokens.
- Tray claims the old capability before sending, conditionally persists the
  replacement into that same record, then refreshes independent controls.
- Coordinated contract, implementation and regressions complete. Walite committed
  as `5ad0b96`; vet/full/race tests pass. All 56 tray tests pass, including 13 GTK.
- Real X11 candidate acceptance passed: repeated/consecutive and alternating
  clicks on the same group/direct records, persisted replacement after tray
  reconstruction, generic focus independence, draft/modal protection followed
  by successful reuse, server-expiry fault injection and Walite restart with
  old history disabled/new notifications working. No real account or sends.
- Deployment COMPLETE: tray `0721674`, Walite `5ad0b96` installed locally as
  `v1.2.1-local.5ad0b96`, both apps restored and running. Installed tray source
  matches; all 56 tests pass against installed package. Settings checksum and
  DND unchanged, private store 0700/0600, zero fixture rows in normal history.
- Previous Walite versions and a code-only pre-v2 tray snapshot retained.
  Linked account/session/cache/configuration not reset, deleted or re-paired.
- Finalize this validation checkpoint locally and remove only disposable test
  directories. No further restart required. No push/tag/release performed.

## Previous task — Walite discussion activation (2026-10-15)

- New request supersedes prior publication authority: **do not push or release**.
  dunst_tray starts clean at `cb89b03` on main. Walite starts clean on
  `fix/notification-chat-navigation` at `77459fd35542c42fb8422b0e5e700506e7e38109`.
- Read the complete Walite integration contract and installation procedure.
  Preserve generic Show app and all history/unread/DND/settings behavior.
- Baseline: 37 discovered dunst_tray tests; 29 pass and 8 GTK tests are skipped
  in headless discovery. Full GTK and Walite checks will run before deployment.
- Plan: bounded strict v1 metadata parsing; record-only private capability
  persistence and migration; owner/permission/symlink/peer-credential-checked
  Unix socket client; a separate Open discussion control; focused integration
  tests. Never log/display capabilities or ChatIDs, or use subprocesses for IPC.
- Protocol limit: no response/acknowledgment exists. Validate/connect/send before
  focusing so known transport failures cannot steal focus. A written request
  does not prove server acceptance; Walite may reject expired/replayed tickets
  or drop navigation while busy. Record actual TUI evidence separately.
- Then commit dunst_tray changes, install it, build the exact Walite commit,
  install code+icon in a new versioned directory while retaining rollback,
  gracefully restart both, and exercise synthetic discussion navigation on X11.
- Implementation and integration tests complete: all 50 tray tests pass,
  including 11 GTK tests, native socket validation, migration, claim-once,
  independent controls and 280px layout. compileall/diff checks pass.
- Walite vet, full tests and race tests pass on the exact supplied commit.
  Production binary built with existing Linux release flags; isolated real-TUI
  fixture built from an archive without modifying Walite's clean checkout.
- Implementation committed as `6a62761`, tray installed through its existing
  installer, settings hash unchanged and history migration verified.
- Walite installed as `v1.2.1-local.77459fd` with official icon/README/license;
  old v1.2.1 retained. Copied binary verification/version/help pass. Both apps
  gracefully restarted, isolated for acceptance, then restored; running binary
  and unique Walite marker verified. DND unchanged. No account data reset.
- Actual installed-package X11 acceptance COMPLETE: physical generic focus
  without navigation/consumption, older group and newer direct selection with
  real rendered-TUI and active-window evidence, draft/modal protection, receiver
  shutdown disabling, 280px controls, history retained. Zero fixture records in
  normal history. Final installed-package 50-test suite passes again.
- Harness corrected for GTK coordinates and queued refresh, full rerun passed.
  See VALIDATION.md for exact evidence and protocol limits. No real-account
  conversation or WhatsApp send was tested; no push/release performed.
- Implementation, deployment and acceptance complete. Save this checkpoint in
  the validation/harness follow-up commit; leave both repositories clean and
  all commits local. Normal applications are restored; no further restart is
  needed. Disposable synthetic build/fixture directories may be removed.

Updated: 2026-10-15 — public GitHub publication verified.
Branch: `main`. Initial verified public commit: `b602d84`.
Initial implementation baseline: `47f79f1`.
Working tree was clean at implementation completion. A subsequent explicit
request authorizes GitHub publication; see the publication checkpoint below.

## Baseline verified

- Commits `fab8a76` (Walite) and `47f79f1` (desktop application activation/icons)
  are present. Source matches the installed UI, activation and application
  resolver files byte for byte. These completed fixes are not being redone.
- All 22 baseline unit tests pass on 2026-10-15.
- Existing configuration: width 380, height 680, margins 48/16, capture enabled,
  retention 100, page size 5. Config mode 0600; launcher and autostart present.
- License is already MIT by the user's earlier explicit choice, commit
  `e601bcb`. The new brief's pending-license sentence is stale; preserve MIT.
- Existing UI keeps unread only in memory and changes the tray bell for DND;
  graphical appearance controls do not yet exist.
- Generic window activation uses exact desktop ID/StartupWMClass and rejects
  missing/ambiguous windows on click. Audit must address the still-enabled
  unverified newest-row Dunst position-0 fallback and accurately label focusing
  an application versus opening a message.

## Phases and current status

1. A/B: focused action/icon audit and synthetic future-aerc coverage — COMPLETE.
2. C: persistent unread state; theme bell with a single white dot — COMPLETE.
3. D: graphical panel settings and atomic persistence — COMPLETE.
4. E/F: full regression and isolated live X11 acceptance — COMPLETE.
5. Install/restart and final checkpoint — COMPLETE.

## Live evidence for this continuation

- 29 pure unit tests pass; 8 opt-in GTK checks all pass with
  `DUNST_TRAY_GUI_TESTS=1` (37 total, 8 skips in default discovery).
- Live X11 focus confirmed with `_NET_ACTIVE_WINDOW` after activation: ChatGPT
  `0x6000004`, Task Manager `0x5600007` (additional generic application), and
  Walite `0x580000e`. Restored focus to ChatGPT afterward.
- Live GTK icon tests: theme icon, absolute synthetic PNG, deleted PNG with
  desktop-entry fallback, missing icon fallback, synthetic future-aerc fixture.
- Dunst service owner remains `:1.44`. Xfce GTK 3.24, compositor active, icon
  theme WhiteSur-Monochrome-Runtime. No Dunst configuration was changed.
- aerc is installed here, but no real aerc notifications were sent or assumed;
  its future-notification scenario was tested only with synthetic metadata.
Reboot/login and i3 checks remain UNVERIFIED; do not reboot the user's desktop.

## Phase C behavior and evidence

- Added persisted unread flags, count, and explicit acknowledgement. Existing
  rows migrate as read; newly captured rows default unread. Restart, retention,
  clear, and read/new-arrival transitions pass pure storage tests.
- Opening the center acknowledges all currently retained rows. New arrivals
  while it is open remain unread until a later explicit opening; closing never
  creates or acknowledges unread rows. DND is independent.
- Bell uses theme foreground with contrast edging, no exclamation or number.
  A white dot is composed in memory, cached by size/color/state. No polling or
  recurring image-file generation. Requested sizes 16/22/24/32 pass pixel and
  dimensional checks for light and dark foregrounds.
- GTK lifecycle/DND/read transitions pass using isolated synthetic history and
  a fake Dunst controller. Actual tray/panel acceptance and visual contrast
  review remain for the final live phase; no reboot/light-panel change claimed.

## Files changed / deployment

Phase A/B commit: `9a0a15b`. Unverified position-0 callbacks
are no longer offered; **Show app** describes verified application focus.
Missing/ambiguous targets are disabled with an explanatory tooltip. Clicks
still revalidate the target. ChatGPT/Walite adapters remain intact.
Installed runtime was upgraded from `47f79f1` after final acceptance; see the
deployment record below. Runtime implementation is through `2a315b7`; tested
deployment payload is `851cf9f` (subsequent commits only document deployment).
Config backup made at
`~/.config/dunst-tray/config.ini.before-appearance-20261015` (not in Git).
Phase C files: model.py, history.py, tray_icon.py, ui.py, installer dependency
check, README, tests/test_history.py, tests/test_gui.py, and this checkpoint.
Phase C commit: `e644294`.

## Phase D completed

- Compact nonblocking GTK settings: opacity 50–100%, width 280–550, height
  300–850, radius 0–24, show icons; Apply, Cancel and Restore Defaults.
- Atomic mode-0600 saving preserves other options. Apply repaints immediately,
  history/DND/capture remain independent; restoring controls does not save.
- Both dimensions fit monitor work areas, including smaller/offset monitors.
  Rounded visual/input clipping applies to the entire window when composited.
  Opaque square fallback without a compositor is implemented, not yet live-tested.
- Found and fixed GTK natural width overriding 280 px. Live GTK check confirms
  exact 280×300 rendering, transparent corner alpha 0, and background alpha
  approximately 128 at 50% opacity. Settings lifecycle, persistence, icon spacing,
  expansion/paging preservation, and malformed-config preservation all pass.
- Visually inspected window-only synthetic center and settings captures plus
  clean/dotted bells at 16/22/24/32 on light/dark sample backgrounds. Layout and
  contrast accepted. This is not a claim of changing/testing the actual light
  Xfce panel. Actual dark-panel XEmbed acceptance remains next.
- Phase D changed config.py, panel.py, settings.py, ui.py, default config,
  config/GTK tests, README, architecture, changelog, and this checkpoint.

## Exact next steps

```sh
cd /path/to/dunst_tray
git status --short
git log -5 --oneline
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Implementation and authorized deployment are complete. On resumption, read
this file, inspect status/log, and run relevant tests before changing anything.
Do not redo completed ChatGPT/Walite work or rerun disruptive live acceptance
unless a new change justifies it. Remaining optional manual acceptance is
listed as UNVERIFIED in docs/VALIDATION.md: login/reboot, i3, actual light panel,
compositor-off, monitor hotplug, real aerc notifications, and long-duration use.
The subsequent publication request authorizes creating a public GitHub remote
and pushing the existing history. No release tag or reboot is requested.

## Publication preparation — 2026-10-15

- Confirmed implementation baseline `e9c6daf`; existing commits are preserved.
- GitHub CLI is installed and authenticated as `antoinebaudrimont-beep` when
  run with network access. The public destination `dunst_tray` does not yet
  exist; this checkout has no remote. No repository has been created or pushed.
- All 37 tests reran successfully with GTK enabled: 29 pure and 8 GTK checks.
  Compilation, installer/uninstaller shell syntax, desktop entry validation,
  and diff whitespace checks also passed. Live desktop acceptance remains the
  previously recorded run, not a new publication-time claim.
- Reworked README for public installation, usage, settings, unread semantics,
  compatibility, testing, privacy, uninstall, and the existing MIT license.
  No screenshots are included rather than publishing personal message images.
- Expanded ignores for SQLite sidecars, local config backups, environment
  files and credentials. Removed the machine-specific checkout path from the
  current checkpoint. Source code, local settings and notification history
  have not been changed by this publication pass.
- Historical audit scanned all 97 existing file blobs. No tested private-key,
  GitHub-token, AWS-key patterns, or known real notification text were found.
  Older WORK_PROGRESS versions contain a local home-directory path; preserving
  history retains those versions. Existing commits also retain their original
  author name/email. The maintainer was informed and subsequently approved
  publishing with their name under the existing account, preserving history.
- README rendered successfully both locally and through GitHub's Markdown
  API: 15 headings, 2 tables, no broken local links. Complete diff reviewed;
  source/scripts/tests/assets/license/package/CI are unchanged.
- Publication preparation committed as `d1a7f2b`; historical metadata privacy
  decision resolved by the maintainer. Public creation, push, and verification
  are complete; see the publication record below.

## Verified public publication — 2026-10-15

- Repository: https://github.com/antoinebaudrimont-beep/dunst_tray
- Created PUBLIC through GitHub CLI using the authenticated account, then
  pushed with ordinary Git. `origin/main` tracks the existing local `main`.
  No force push, rewritten commits, replacement project, tag, or release.
- Initial pushed/verified commit:
  `b602d843a925fcf0586db4ee3482884ac35ba445`. Original baseline `e9c6daf` remains
  its ancestor. Subsequent publication-record-only commits retain that history.
- Remote and local main commit IDs matched. All 40 tracked file paths/blob
  hashes matched GitHub's complete tree, including application source and MIT
  license. The repository returned HTTP 200 without authentication.
- GitHub rendered the published README successfully (15 headings, 2 tables).
  All local documentation links resolved. GitHub Actions completed successfully
  for the initial push; its existing workflow runs pure checks on Python 3.11
  and 3.13 and skips opt-in GTK checks.
- Publication-time local validation: all 37 tests pass with GTK enabled; shell
  syntax, compilation, desktop entry validation and whitespace checks pass.
  Earlier live validation remains separately documented and was not rerun.
- Changed only README.md, .gitignore, docs/PUBLISHING.md, and this checkpoint.
  Application source, scripts, tests, assets, CI and MIT license are unchanged.
  Installed settings and local notification history were not modified.
- Screenshots were omitted rather than exposing real notifications. Current
  public documentation contains no machine-specific home path. The maintainer
  explicitly approved preserving existing historical metadata after disclosure.
- Remaining compatibility gaps are unchanged: reboot/login, i3, real aerc
  notifications, and the other UNVERIFIED checks in docs/VALIDATION.md.
- Publication is complete. Resume with `git status`, `git log`, and ordinary
  non-force updates only when requested; the final handoff supplies the latest
  verified commit after this publication record is pushed.

## Final acceptance completed before deployment

- Phase D commit: `2a315b7`. All 37 tests passed with GUI enabled; no skips.
- Added reusable `scripts/check_live.py`. Actual Xfce/Dunst acceptance passed:
  clean/one/20 unread, physical bell toggle, arrivals while open, actual DND,
  unread restoration, physical appearance Apply/Cancel, appearance restoration,
  physical Show app for ChatGPT/Task Manager/Walite with exact active-window
  confirmation, local history clear, and persistent bell.
- Dunst owner remained `:1.44`; pause level restored to 0; original focus
  restored. No Dunst configuration was edited. Installed config still compares
  byte-for-byte with the saved backup.
- Auto-review initially rejected potential daemon-history deletion. Safer
  script now makes the daemon clear method an explicit no-op and issues no
  daemon-history-delete command. Only own transient Notify IDs are closed.
  The revised run was approved and passed. User Dunst history was not cleared.
- The old installed tray was stopped during synthetic calls and restored as
  PID 48984 afterward. Installed code is still the old baseline until the next
  deployment step. Temporary test history was deleted by the script.
- Exact outcomes and honest UNVERIFIED checks are in `docs/VALIDATION.md`.
  In particular: no reboot/login/i3/light-panel/compositor-off/hotplug claim;
  aerc remains a synthetic future-compatibility fixture, and **Show app** is
  application focus rather than a private exact-message callback.

## Final deployment record

- Installed via `./scripts/install.sh` and restarted only the identified old
  tray PID 48984. New running tray PID 50439 holds the instance lock, owns the
  Dunst Tray XEmbed window, and logged passive capture started successfully.
- All installed `src/dunst_tray/*.py` files compare byte-for-byte with source.
  Config and backup remain mode 0600 and byte-identical; autostart entry remains
  present at mode 0644. Existing user preferences were not replaced.
- User database migration succeeded (unread column present). Only aggregate
  counts were inspected: zero retained/unread at this check. No notification
  text was printed, saved in Git, or included in screenshots.
- Actual installed clean bell was captured window-only and visually checked.
  Its real right-click menu opened **Notification Center Appearance**, verified
  to belong to PID 50439; dialog displayed the preserved effective defaults
  (380×680, 97%, radius 14, icons shown). Closed with Escape without saving.
- Dunst owner still `:1.44`; pause level still 0. Dunst configuration and
  history were not cleared or changed by deployment.
- Temporary preview scripts, synthetic preview images, and startup logs were
  cleaned up. Reusable synthetic checks remain in tests/ and
  scripts/check_live.py; no runtime data or screenshots are tracked.
- Stable phase commits: audit `9a0a15b`, unread `e644294`, appearance `2a315b7`,
  final acceptance `851cf9f`. Original fixes `fab8a76` / `47f79f1` preserved.
