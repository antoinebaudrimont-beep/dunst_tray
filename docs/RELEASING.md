# Beta source release procedure

Release tag: **v0.1.0-beta.1**. Runtime/PEP 440 version: **0.1.0b1**.
This is a **beta prerelease**, not a stable or latest release. No binary, Debian,
PyPI package or bundled Walite is provided.

## Reproducible archive

From a reviewed committed snapshot, using Python 3.11+, Git and zlib:

```sh
python3 scripts/build_source_release.py --ref HEAD --output dist/first
python3 scripts/build_source_release.py --ref HEAD --output dist/second
cmp dist/first/dunst-tray-0.1.0-beta.1.tar.gz dist/second/dunst-tray-0.1.0-beta.1.tar.gz
(cd dist/first && sha256sum -c SHA256SUMS)
```

The archive contains the committed source tree (including tests, docs, native
screenshots, installer/uninstaller, assets and MIT license), never untracked or
ignored runtime files or `.git`. `git archive` fixes ownership and uses the
commit timestamp; gzip uses timestamp zero, no filename and compression level 9.
The embedded Git archive commit identifies the exact source. Rebuilding the same
commit with the same Git/zlib toolchain is byte-for-byte reproducible. Different
compression implementations/versions may produce different compressed bytes.
Existing output files are never overwritten. The checksum file lists the
versioned archive; it is not a cryptographic signature or an authentication key.
GitHub's automatically generated source downloads are separate, not these
curated/checksummed assets.

## Isolated installation acceptance

Requires Linux user namespaces, `bubblewrap`, existing runtime dependencies and
the prior published `4cd15f4` commit locally. No package is installed system-wide.

```sh
python3 scripts/validate_source_install.py dist/first/dunst-tray-0.1.0-beta.1.tar.gz
```

The validator **never runs installers outside bubblewrap**; sandbox failure is
fatal, with no fallback to the host. A private writable filesystem hides the
normal home without reassigning HOME. Private XDG state, a read-only host root,
private `/tmp`, `/run`, PID and network namespaces, and no display/session bus
prevent access to installed applications, normal notification history or Dunst.
Only disposable synthetic state is created and purged.

Acceptance checks:

- Install previous public source; seed fictional SQLite history with unread
  state and a custom preference plus synthetic Dunst config.
- Upgrade using the extracted beta archive. Verify runtime version, every
  installed Python source, required assets/docs/license, executable launcher,
  autostart paths, private config/data permissions, CLI help and version.
- Compare preferences/history byte-for-byte; reopen only the synthetic DB to
  verify its notification and unread state. No normal app is started.
- Default uninstall preserves state; reinstall preserves it; explicit purge
  removes only sandbox state. Clean beta installation restores defaults.
- Synthetic Dunst configuration remains unchanged through every operation.

This validates file installation/upgrade/removal, not reboot behavior or a new
desktop environment. Existing Xfce/X11 acceptance is recorded separately in
[VALIDATION.md](VALIDATION.md); i3 remains unverified and Wayland unsupported.

## Publication gates

1. Review all changes and images for privacy. Run all tests, syntax and archive
   checks. Verify matching versions and repeatable archive bytes/checksums.
2. Run isolated install acceptance against the **final committed artifact**.
3. Fetch current remote main; push only a safe fast-forward and verify CI for
   the exact final commit (Python 3.11 and 3.13).
4. Create an annotated `v0.1.0-beta.1` tag at that commit; push that tag without
   force. Verify its CI. Never overwrite a published tag/artifact.
5. Use [the curated notes](releases/v0.1.0-beta.1.md). Upload the archive and
   `SHA256SUMS` to a draft, then publish explicitly as a **prerelease**, not latest.
6. Verify anonymous public release access, all three tag-pinned screenshot URLs
   and both asset download URLs. Recompute the downloaded archive SHA-256 and
   compare with downloaded `SHA256SUMS` and local artifact. Do not publish if a
   validation gate fails. No installed applications need to be changed.
