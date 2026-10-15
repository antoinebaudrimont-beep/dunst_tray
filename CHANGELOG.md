# Changelog

All notable changes will be documented here. The project follows Semantic
Versioning once releases are tagged.

## Unreleased

### Added

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

