# Work progress — resumable implementation

Updated: 2026-10-15 10:17 CEST (Europe/Vienna).
Branch: `main`. HEAD before phase D commit: `e644294`.
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
4. E/F: full regression, isolated live X11 acceptance, install/restart — NEXT.

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
Installed application remains at `47f79f1` until final stable deployment.
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

Run the full suite with GUI enabled, then a short isolated live passive-capture
acceptance with actual Dunst and Xfce tray: zero/one/20 unread, opening/closing,
DND, restart persistence, real mouse activation, settings repaint/persistence,
clear without clearing user Dunst history. Stop the installed old tray during
synthetic capture so it cannot retain fixtures. Clean only known synthetic
Dunst IDs. Preserve/restore the user's pause level and focus. Then install and
restart the validated build, compare installed files, verify the running PID,
record exact results and remaining manual gaps, and commit the final checkpoint.
