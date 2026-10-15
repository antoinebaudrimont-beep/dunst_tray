# Work progress — resumable implementation

Updated: 2026-10-15 10:08 CEST (Europe/Vienna).
Branch: `main`. HEAD before phase C commit: `9a0a15b`.
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
3. D: graphical panel settings and atomic persistence — NEXT.
4. E/F: full regression, isolated live X11 acceptance, install/restart — pending.

## Live evidence for this continuation

- 26 pure unit tests pass; 5 opt-in GTK checks are skipped in default discovery
  and all 5 pass with `DUNST_TRAY_GUI_TESTS=1` (31 total).
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
Installed application remains at `47f79f1` until final stable deployment.
Config backup made at
`~/.config/dunst-tray/config.ini.before-appearance-20261015` (not in Git).
Phase C files: model.py, history.py, tray_icon.py, ui.py, installer dependency
check, README, tests/test_history.py, tests/test_gui.py, and this checkpoint.

## Exact next steps

```sh
cd /home/nupnus/Documents/Codex/2026-10-15/files-pasted-by-the-user-project/dunst-tray
git status --short
git log -5 --oneline
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Begin phase D. Extend validated configuration with opacity, radius and icon
visibility; atomically persist Apply while preserving unrelated settings. Add
compact GTK appearance controls with Apply/Cancel/Restore Defaults. Apply to the
center immediately without changing Dunst/history, clamp both dimensions to
monitor work area, and verify compositor clipping. Add focused tests, update
this checkpoint and commit before final live acceptance/deployment.
