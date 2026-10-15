# Work progress — resumable implementation

Updated: 2026-10-15 10:26 CEST (Europe/Vienna).
Branch: `main`. HEAD before final deployment record: `851cf9f`.
Initial implementation baseline: `47f79f1`.
Working tree was clean. No remote, publication, or release operation is planned.

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
cd /home/nupnus/Documents/Codex/2026-10-15/files-pasted-by-the-user-project/dunst-tray
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
No remote, push, tag, or reboot is authorized by this work.

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
