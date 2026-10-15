# Work progress — resumable implementation

Updated: 2026-10-15 10:10 CEST (Europe/Vienna).
Branch: `main`. HEAD before phase A/B commit: `a21943a`.
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
2. C: persistent unread state; theme bell with a single white dot — NEXT.
3. D: graphical panel settings and atomic persistence — pending.
4. E/F: full regression, isolated live X11 acceptance, install/restart — pending.

## Live evidence for this continuation

- 24 pure unit tests pass; 3 opt-in GTK checks are skipped in default discovery
  and pass when run with `DUNST_TRAY_GUI_TESTS=1`.
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

## Files changed / deployment

Phase A/B changes: activation.py, ui.py, tests/test_activation.py,
tests/test_gui.py, README, and this checkpoint. Unverified position-0 callbacks
are no longer offered; **Show app** describes verified application focus.
Missing/ambiguous targets are disabled with an explanatory tooltip. Clicks
still revalidate the target. ChatGPT/Walite adapters remain intact.
Installed application remains at `47f79f1` until final stable deployment.
Config backup made at
`~/.config/dunst-tray/config.ini.before-appearance-20261015` (not in Git).

## Exact next steps

```sh
cd /home/nupnus/Documents/Codex/2026-10-15/files-pasted-by-the-user-project/dunst-tray
git status --short
git log -5 --oneline
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Begin phase C. Add an unread column with safe migration, store-level count and
mark-read operations, then compose a theme-aware bell with one white dot in
memory. Define opening-center/read behavior; DND must not affect unread. Add
focused persistence and transition tests and GTK icon-render checks at
16/22/24/32 px. Update this checkpoint and commit the working phase.
