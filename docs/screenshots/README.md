# Screenshot provenance and privacy review

Captured 2026-10-16 for the proposed **v0.1.0-beta.1** prerelease. These are
native GTK3/X11 framebuffer captures, not generated images or reconstructed UI.
The application Python sources are unchanged from `4cd15f4`.

## Images

| File | Native size | Bytes | Contents |
| --- | --- | ---: | --- |
| [notification-center.png](notification-center.png) | 474 × 886 | 48,730 | Three app groups; five expanded fictional messages; Show older (2); icons; genuine Show app/Open discussion controls. |
| [settings.png](settings.png) | 498 × 494 | 30,182 | Actual Settings with appearance options; auto-hide enabled and applied at five seconds; Apply/Cancel/Restore Defaults. |
| [desktop-integration.png](desktop-integration.png) | 1120 × 960 | 56,850 | Real Xfce panel, unread bell, open center and a plain temporary desktop background. |

Click for native-resolution details. Small action labels are intentionally not
redrawn or enlarged inside the images. README previews link to the full PNGs.

## Capture integrity

- A separate **Xvfb X11 server**, with an Xauthority cookie and no TCP listener,
  runs the real xfwm4 compositor, xfce4-panel, Dunst and production GTK UI.
  This is an isolated X11/Xfce session, not a claim of physical-screen capture
  from the personal desktop.
- Separate session D-Bus and temporary XDG config/data/cache/runtime directories
  prevent host notifications/settings from entering the capture session.
  Normal applications stay running. No personal notification database is opened
  or copied; the actual Dunst configuration is never read or modified.
- The installed desktop's GTK theme/font were read only and mirrored in the
  isolated process: **WhiteSur-Dark-solid-pink**, **Noto Sans 9.5**. No application
  CSS, layout, action availability or production behavior was modified.
- Fictional Walite notifications come from the existing offline production-TUI
  fixture built in an archive of compatible Walite `5ad0b96`. Screenshot mode
  changes only fixture display text. There is no WhatsApp client/account or
  message sending. Real group/direct navigation and fresh ticket rotation were
  exercised before capture; controls were not mocked or forced enabled.
- Calendar and browser examples are synthetic Notify calls with installed
  temporary desktop identities and real, uniquely identified fixture windows.
- The unread dot is real: a new fictional Calendar notification arrives after
  opening the center. Opening acknowledges existing rows; the new row remains
  unread. No badge or indicator was painted into the PNG.
- Each PNG is saved directly from the actual framebuffer, with bounds-only
  cropping for the center/settings and lossless PNG compression level 9.
  Decoded pixels are compared with the captured pixels. No compositing,
  resizing, retouching, blur, generated UI or pasted controls are used.

## Per-image privacy review

All three final files were opened and visually inspected at native resolution.
Only fictional **Mira Fern / Luma Trails Club** fixture data and example
Calendar/browser text are used. There are no real contact names, private
conversations, email addresses, phone numbers, filesystem paths, usernames,
hostnames, terminal contents, personal wallpaper or unexpected desktop windows.

All PNG chunks and CRCs were inspected. The only chunks are `IHDR`, `sBIT`,
`IDAT` and `IEND`: no EXIF, XMP, text/comments, author/software fields, timestamps,
location, profiles or embedded paths. `tests/test_screenshots.py` guards the
allowlist, image dimensions/integrity, file-size budget and documentation links.
Visible notification dates are ordinary synthetic notification timestamps,
not hidden image metadata.

SHA-256:

```text
0a9b474bb20251556b18071fa0c9faf32ef33b26a9db495c93e4e015c9359e63  notification-center.png
a31b9b63fc42ad75e9428c6381d5b4a647c58d2a6a144231c45b99808a3aafb4  settings.png
2c8c5a13a26225d2af8310639974fe5fb170a988801cbfc9903a6eb8556e2781  desktop-integration.png
```

## Reproduction

Capture tools are optional development dependencies, not new runtime needs:
Xvfb, xauth, xfce4-panel, xfwm4, xterm, feh, xdotool and x11-utils, plus the usual
GTK/Dunst dependencies. For this run a trusted Debian Xvfb package was unpacked
only in a disposable folder; no system package was installed.

Build the existing Go fixture using the isolated archive procedure in
[WALITE.md](../WALITE.md), copying the current `walite_navigation_test.go` with
its opt-in fictional-data mode. Then, from the repository:

```sh
PYTHONPATH=src python3 scripts/capture_screenshots.py \
  --xvfb /path/to/Xvfb \
  --walite-fixture /path/to/offline/walite-fixture \
  --theme WhiteSur-Dark-solid-pink --font 'Noto Sans 9.5'
```

The default stock-theme alternative is Greybird-dark / Sans 10; geometry may
differ, so inspect new captures before replacing these reviewed artifacts.
The harness isolates the display/bus/data, validates real navigation, captures
three images and closes only its own processes/temporary data. It does not
install, stop or restart the normal tray or Walite. `feh --no-fehbg` also avoids
writing the user's wallpaper startup file.

## Publication status

Images and README changes are **local preparation for review**, not published.
The [draft prerelease description](../releases/v0.1.0-beta.1.md) includes all
three captures using future tag-pinned absolute image URLs (relative image
paths are unsuitable in a release body). Those URLs cannot resolve publicly
until the approved files/tag are published. No tag or release was created.
