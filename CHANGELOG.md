# Changelog

All notable changes will be documented here. The project follows Semantic
Versioning once releases are tagged.

## Unreleased

No changes yet.

## 0.1.0-beta.1 — 2026-10-16

First public **beta**; Python/package version `0.1.0b1`. Tested on MX Linux /
Debian Trixie / Xfce / X11; Wayland unsupported and i3 not verified.

### Added

- Reproducible committed-source archive, SHA-256 checksums, packaging guards
  and isolated installation/upgrade/removal validation without touching a live
  installation. No binary, Debian or PyPI package is supplied in this beta.
- Privacy-reviewed native GTK3/Xfce screenshots, a reproducible isolated capture
  harness, PNG metadata/link guards and a first-prerelease gallery.
- Optional inactivity auto-hide (off by default, 5 seconds, range 3–120), with
  interaction/Settings/modal holds, persistent preferences and GTK timer tests.
- Conservative foreground-PTY process identity fallback for terminal desktop
  apps, without executing notification text or desktop commands.
- Repeatable Walite discussion navigation through coordinated v2 one-use ticket
  rotation, without replay or lifetime extension; generic Show app is unchanged.
- Walite v1 opaque-ticket discussion navigation, independent of generic
  application focus, with private Unix socket verification and integration tests.
- Persistent unread state and a clean tray bell with one white dot for unread
  messages, independent of Do Not Disturb.
- GTK appearance settings with Apply/Cancel/Restore Defaults, atomic saving,
  work-area size fitting, background opacity, rounded clipping, and icon toggle.
- Initial GTK3 tray application and grouped notification center.
- Passive D-Bus capture with private, bounded SQLite persistence.
- Dunst pause, replay, clear-history, and action controls.
- Local install, autostart, and uninstall tooling.

### Fixed

- Offer Show app independently of notification callbacks, including aerc's
  no-action notifications; explain unavailable message-level navigation.
- Disable unverified notification callbacks and missing/ambiguous app targets;
  label verified window focusing **Show app**.
- Preserve expanded groups, paging, and scroll during visible updates, and
  coalesce notification bursts without polling.
- Resolve installed application icons when notifications omit their icon,
  including existing ChatGPT history entries.
- Activate running installed desktop applications from retained notifications
  by X11 application class, including ChatGPT after its popup callback expires.
- Preserve desktop-entry identity and migrate existing history without losing
  messages.
- Enable **Open** on every retained Walite notification and raise Walite via
  its validated X11 marker after the original Dunst callback has expired.

