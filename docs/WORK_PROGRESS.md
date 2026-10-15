# Work progress — resumable implementation

Updated: 2026-10-15 10:01 CEST (Europe/Vienna).
Branch: `main`. HEAD at initial inspection: `47f79f1`.
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

1. A/B: focused action/icon audit and synthetic future-aerc coverage — NEXT.
2. C: persistent unread state; theme bell with a single white dot — pending.
3. D: graphical panel settings and atomic persistence — pending.
4. E/F: full regression, isolated live X11 acceptance, install/restart — pending.

## Live evidence for this continuation

No new live acceptance is claimed yet. Prior evidence remains in
`docs/VALIDATION.md`; baseline file comparisons and tests were rerun.
Reboot/login and i3 checks remain UNVERIFIED; do not reboot the user's desktop.

## Files changed / deployment

Only this checkpoint file has changed. Installed application remains at
`47f79f1`. Before deployment, back up the installed config without storing it
in Git. Use synthetic data in all fixtures and screenshots.

## Exact next steps

```sh
cd /home/nupnus/Documents/Codex/2026-10-15/files-pasted-by-the-user-project/dunst-tray
git status --short
git log -5 --oneline
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Inspect the live Dunst service owner, X11 identities, and panel theme. Add only
focused uncovered action/icon regressions. Disable unresolvable action targets
and describe application focus honestly. Run one additional installed-app X11
focus check if feasible, record evidence here, commit the stable phase, then
start persistent unread state. Update this file after each coherent step.
