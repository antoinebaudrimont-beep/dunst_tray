#!/usr/bin/env python3
"""Opt-in install/upgrade/removal validation in a disposable bubblewrap sandbox.

Never runs an installer outside the sandbox. HOME is not reassigned: a private
filesystem is mounted over that location, with private XDG state, PID/network
namespaces, no desktop/bus access and read-only system directories. Requires bwrap and
the ordinary installed system dependencies. No app is launched or restarted.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def unpack(archive: Path, target: Path) -> Path:
    with tarfile.open(archive) as source:
        for member in source.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe source archive")
        source.extractall(target, filter="data")
    entries = list(target.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        raise ValueError("Source archive must have one top-level directory")
    return entries[0]


def outside(archive: Path, previous: str):
    if not shutil.which("bwrap"):
        raise RuntimeError("bubblewrap is required; no unsafe fallback is attempted")
    with tempfile.TemporaryDirectory(prefix="dunst-release-validation-") as temporary:
        temporary = Path(temporary)
        for name in ("current", "previous", "home", "work"):
            (temporary / name).mkdir()
        current = unpack(archive.resolve(), temporary / "current")
        previous_archive = temporary / "previous.tar"
        with previous_archive.open("wb") as handle:
            subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar",
                            "--prefix=previous/", previous], stdout=handle, check=True)
        old = unpack(previous_archive, temporary / "previous")
        work = temporary / "work"
        (work / "SANDBOX_MARKER").write_text("disposable release validation\n")
        for name in ("config", "data", "cache", "runtime"):
            (work / name).mkdir(mode=0o700)
        # Source paths resolve in the host before bubblewrap enters its sandbox.
        command = ["bwrap", "--unshare-all", "--new-session", "--die-with-parent",
                   "--hostname", "release-fixture", "--tmpfs", "/",
                   "--ro-bind", "/usr", "/usr", "--ro-bind", "/etc", "/etc",
                   "--symlink", "usr/bin", "/bin", "--symlink", "usr/sbin", "/sbin",
                   "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
                   "--dir", "/home", "--dir", "/root", "--tmpfs", "/tmp",
                   "--tmpfs", "/run", "--proc", "/proc", "--dev", "/dev",
                   "--dir", str(Path.home()), "--bind", str(temporary / "home"), str(Path.home()),
                   "--ro-bind", str(current), "/release", "--ro-bind", str(old), "/previous",
                   "--bind", str(work), "/work", "--chdir", "/work"]
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "DBUS_SYSTEM_BUS_ADDRESS",
                     "PYTHONPATH", "DUNST_TRAY_APP_DIR", "PYTHONHOME"):
            command += ["--unsetenv", name]
        for name, value in (("XDG_CONFIG_HOME", "/work/config"), ("XDG_DATA_HOME", "/work/data"),
                            ("XDG_CACHE_HOME", "/work/cache"), ("XDG_RUNTIME_DIR", "/work/runtime"),
                            ("PYTHONDONTWRITEBYTECODE", "1"), ("PATH", "/usr/bin:/bin")):
            command += ["--setenv", name, value]
        command += ["/usr/bin/python3", "/release/scripts/validate_source_install.py", "--inside"]
        subprocess.run(command, check=True, timeout=90)


def inside():
    assert Path("/work/SANDBOX_MARKER").read_text() == "disposable release validation\n"
    assert Path("/proc/1/root").exists()
    assert not os.environ.get("DISPLAY") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    assert os.environ["XDG_RUNTIME_DIR"] == "/work/runtime"
    user_dir = Path.home()
    assert list(user_dir.iterdir()) == [], "Sandbox home must initially be empty"
    app = user_dir / ".local/opt/dunst-tray"
    launcher = user_dir / ".local/bin/dunst-tray"
    config = Path("/work/config/dunst-tray/config.ini")
    database = Path("/work/data/dunst-tray/history.sqlite3")
    autostart = Path("/work/config/autostart/dunst-tray.desktop")
    dunst = Path("/work/config/dunst/dunstrc")
    dunst.parent.mkdir()
    dunst.write_text("# Synthetic untouched Dunst configuration\n")
    original_dunst = dunst.read_bytes()

    def run(*arguments):
        return subprocess.check_output(arguments, text=True, stderr=subprocess.STDOUT)

    def install(source):
        run("/bin/sh", source + "/scripts/install.sh")
        assert config.stat().st_mode & 0o777 == 0o600
        assert database.parent.stat().st_mode & 0o777 == 0o700
        assert autostart.exists() and launcher.is_file()
        assert os.access(launcher, os.X_OK)
        assert str(launcher) in autostart.read_text()
        assert dunst.read_bytes() == original_dunst

    # Clean install of the previously published version, then realistic state.
    install("/previous")
    assert run(str(launcher), "--version").strip() == "0.1.0.dev0"
    config.write_text(config.read_text() + "\n[custom]\nkeep = synthetic-preference\n")
    config_bytes = config.read_bytes()
    sys.path.insert(0, str(app / "src"))
    from dunst_tray.history import HistoryStore
    from dunst_tray.model import Notification
    history = HistoryStore(database)
    history.add(Notification(id=None, received_at=1.0, app_name="Fictional Calendar",
                             replaces_id=0, app_icon="", summary="Synthetic upgrade fixture",
                             body="No private notification content", actions=(), urgency=1,
                             expire_timeout=5000, unread=True))
    history.close()
    database_hash = hashlib.sha256(database.read_bytes()).digest()

    def preserved():
        assert config.read_bytes() == config_bytes
        assert hashlib.sha256(database.read_bytes()).digest() == database_hash
        assert dunst.read_bytes() == original_dunst

    # Upgrade, verify installed sources/assets/version, help, and no started app.
    install("/release")
    preserved()
    assert run(str(launcher), "--version").strip() == "0.1.0b1"
    assert "--database" in run(str(launcher), "--help")
    for source in Path("/release/src/dunst_tray").glob("*.py"):
        assert source.read_bytes() == (app / "src/dunst_tray" / source.name).read_bytes()
    for relative in ("pyproject.toml", "README.md", "CHANGELOG.md", "LICENSE",
                     "assets/default-config.ini", "docs/dunst-integration.conf"):
        assert (app / relative).read_bytes() == (Path("/release") / relative).read_bytes()
    assert list(Path("/work/runtime").iterdir()) == []
    # Open only the synthetic upgraded DB; check retained unread/history state.
    history = HistoryStore(database)
    assert history.count() == 1 and history.latest().unread
    assert history.latest().summary == "Synthetic upgrade fixture"
    history.close()
    database_hash = hashlib.sha256(database.read_bytes()).digest()
    # Default uninstall preserves preferences/history; reinstall also preserves.
    run("/bin/sh", "/release/scripts/uninstall.sh")
    assert not app.exists() and not launcher.exists() and not autostart.exists()
    preserved()
    install("/release")
    preserved()
    # Purge operates only on this disposable sandbox's synthetic state.
    run("/bin/sh", "/release/scripts/uninstall.sh", "--purge")
    assert not config.parent.exists() and not database.parent.exists()
    assert not app.exists() and not launcher.exists() and not autostart.exists()
    assert dunst.read_bytes() == original_dunst
    # Final clean beta install checks default auto-hide and CLI version.
    install("/release")
    assert "auto_hide = false" in config.read_text()
    assert run(str(launcher), "--version").strip() == "0.1.0b1"
    run("/bin/sh", "/release/scripts/uninstall.sh", "--purge")
    assert not app.exists() and not launcher.exists() and not autostart.exists()
    print("PASS clean beta install; upgrade from 4cd15f4; exact installed source/version/assets")
    print("PASS preferences/history/unread preservation; default uninstall; reinstall; isolated purge")
    print("PASS Dunst unchanged; no display/session bus/network; no app launched; host home hidden")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, nargs="?")
    parser.add_argument("--previous-ref", default="4cd15f4")
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    arguments = parser.parse_args()
    if arguments.inside:
        inside()
    elif arguments.archive:
        outside(arguments.archive, arguments.previous_ref)
    else:
        parser.error("Pass a verified source archive")
