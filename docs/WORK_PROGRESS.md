# Work progress — resumable implementation

## Current task — Walite discussion activation (2026-10-15)

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
