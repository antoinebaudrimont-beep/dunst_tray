"""Release version and reproducible committed-source packaging guards."""
from __future__ import annotations

import gzip
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import unittest

from dunst_tray import __version__

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_release", ROOT / "scripts/build_source_release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseTests(unittest.TestCase):
    def test_beta_versions_and_documentation_agree(self):
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual(__version__, release.VERSION)
        self.assertEqual(metadata["project"]["version"], release.VERSION)
        self.assertIn("Development Status :: 4 - Beta", metadata["project"]["classifiers"])
        for name in ("README.md", "CHANGELOG.md", "docs/releases/" + release.TAG + ".md"):
            self.assertIn(release.VERSION, (ROOT / name).read_text())
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())

    @unittest.skipUnless(shutil.which("git"), "Git is needed for source archive tests")
    def test_archive_is_reproducible_complete_and_excludes_uncommitted_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repo"
            # The source archive includes tests/docs/assets as well as the app.
            shutil.copytree(ROOT, repository, ignore=shutil.ignore_patterns(
                ".git", "__pycache__", "dist", "build", "*.egg-info"))
            def git(*args):
                return subprocess.run(["git", "-C", str(repository), *args], check=True,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            git("init", "-q")
            git("add", ".")
            git("-c", "user.name=Release Test", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", "Synthetic packaging fixture")
            (repository / "private-untracked.txt").write_text("Synthetic excluded data")
            (repository / "README.md").write_text("Uncommitted text must not enter the archive")
            first, digest = release.build(repository, root / "one")
            second, second_digest = release.build(repository, root / "two")
            self.assertEqual(digest, second_digest)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes()[4:8], b"\0" * 4)  # gzip timestamp
            self.assertEqual((root / "one/SHA256SUMS").read_text(), f"{digest}  {release.ARCHIVE}\n")
            self.assertTrue(gzip.decompress(first.read_bytes()))
            with tarfile.open(first) as archive:
                names = archive.getnames()
                self.assertFalse(any("private-untracked" in name or "/.git/" in name for name in names))
                self.assertEqual(archive.extractfile(release.PREFIX + "/README.md").read(),
                                 (ROOT / "README.md").read_bytes())
                installer = archive.getmember(release.PREFIX + "/scripts/install.sh")
                self.assertTrue(installer.mode & 0o111)
                self.assertTrue(all(item.uid == 0 and item.gid == 0 for item in archive.getmembers()))
            with self.assertRaises(FileExistsError):
                release.build(repository, root / "one")

    @unittest.skipUnless(shutil.which("git"), "Git is needed for source archive tests")
    def test_wrong_committed_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            (repository / "src/dunst_tray").mkdir(parents=True)
            (repository / "pyproject.toml").write_text('[project]\nversion="0.0.0"\n')
            (repository / "src/dunst_tray/__init__.py").write_text('__version__="0.0.0"\n')
            for args in (("init", "-q"), ("add", "."),
                         ("-c", "user.name=Release Test", "-c", "user.email=fixture@example.invalid",
                          "commit", "-qm", "Synthetic wrong version")):
                subprocess.run(["git", "-C", str(repository), *args], check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with self.assertRaisesRegex(ValueError, "versions"):
                release.build(repository, repository / "output")
