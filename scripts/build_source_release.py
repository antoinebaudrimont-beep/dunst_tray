#!/usr/bin/env python3
"""Build a deterministic beta source archive from a committed Git snapshot.

Only committed blobs enter the archive, never the working tree, Git directory,
user configuration or notification history. No network or installation occurs.
"""
from __future__ import annotations

import argparse
import ast
import gzip
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile
import tomllib

TAG = "v0.1.0-beta.1"
VERSION = "0.1.0b1"
PREFIX = "dunst-tray-0.1.0-beta.1"
ARCHIVE = PREFIX + ".tar.gz"
ROOT = Path(__file__).resolve().parents[1]


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repository), *arguments])


def build(repository: Path, output: Path, ref: str = "HEAD") -> tuple[Path, str]:
    commit = git(repository, "rev-parse", "--verify", "--end-of-options",
                 ref + "^{commit}").decode().strip()
    metadata = tomllib.loads(git(repository, "show", commit + ":pyproject.toml").decode())
    module = ast.parse(git(repository, "show", commit + ":src/dunst_tray/__init__.py"))
    runtime = next(ast.literal_eval(node.value) for node in module.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "__version__"
                           for target in node.targets))
    if metadata["project"]["version"] != VERSION or runtime != VERSION:
        raise ValueError("Committed package/runtime versions must both be " + VERSION)
    raw = git(repository, "-c", "tar.umask=0022", "archive", "--format=tar",
              "--prefix=" + PREFIX + "/", commit)
    required = {"pyproject.toml", "README.md", "CHANGELOG.md", "LICENSE",
                "scripts/install.sh", "scripts/uninstall.sh", "assets/dunst-tray.in",
                "assets/default-config.ini", "assets/dunst-tray.desktop",
                "src/dunst_tray/__init__.py", "docs/releases/" + TAG + ".md"}
    with tarfile.open(fileobj=io.BytesIO(raw)) as source:
        names = set()
        for member in source.getmembers():
            path = Path(member.name)
            if (path.is_absolute() or ".." in path.parts or path.parts[0] != PREFIX
                    or not (member.isfile() or member.isdir())):
                raise ValueError("Unsafe source archive member")
            if ".git" in path.parts or path.suffix in {".db", ".sqlite", ".sqlite3", ".pem", ".key"}:
                raise ValueError("Private/runtime file in committed source tree")
            if member.isfile():
                names.add(path.relative_to(PREFIX).as_posix())
        if not required <= names:
            raise ValueError("Incomplete source snapshot")
    output.mkdir(parents=True, exist_ok=True)
    target = output / ARCHIVE
    if target.exists() or (output / "SHA256SUMS").exists():
        raise FileExistsError("Use a new output directory; existing artifacts are not overwritten")
    with target.open("xb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0,
                           compresslevel=9) as compressed:
            compressed.write(raw)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(f"{digest}  {ARCHIVE}\n", encoding="ascii")
    print(f"Source commit: {commit}\n{digest}  {ARCHIVE}")
    return target, digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="Committed Git snapshot (default HEAD)")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    arguments = parser.parse_args()
    build(ROOT, arguments.output, arguments.ref)
