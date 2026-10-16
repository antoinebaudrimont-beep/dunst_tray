"""Publication guards for native, metadata-free screenshot artifacts."""
from __future__ import annotations

import struct
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = {
    "notification-center.png": (474, 886),
    "settings.png": (498, 494),
    "desktop-integration.png": (1120, 960),
}


class ScreenshotTests(unittest.TestCase):
    def test_pngs_have_valid_pixels_and_no_private_metadata_chunks(self):
        for name, dimensions in IMAGES.items():
            with self.subTest(image=name):
                data = (ROOT / "docs/screenshots" / name).read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertLess(len(data), 120_000)
                offset, chunks, compressed = 8, [], bytearray()
                while offset < len(data):
                    size, kind = struct.unpack(">I4s", data[offset:offset + 8])
                    body = data[offset + 8:offset + 8 + size]
                    crc = struct.unpack(">I", data[offset + 8 + size:offset + 12 + size])[0]
                    self.assertEqual(zlib.crc32(kind + body) & 0xffffffff, crc)
                    # No text, EXIF, XMP, timestamps, author paths or comments.
                    self.assertIn(kind, {b"IHDR", b"sBIT", b"IDAT", b"IEND"})
                    if kind == b"IHDR":
                        self.assertEqual(struct.unpack(">II", body[:8]), dimensions)
                    elif kind == b"IDAT":
                        compressed.extend(body)
                    chunks.append(kind)
                    offset += size + 12
                self.assertEqual(offset, len(data))
                self.assertEqual(chunks[0], b"IHDR")
                self.assertEqual(chunks[-1], b"IEND")
                self.assertTrue(zlib.decompress(compressed))

    def test_readme_and_release_notes_reference_every_capture(self):
        readme = (ROOT / "README.md").read_text()
        notes = (ROOT / "docs/releases/v0.1.0-beta.1.md").read_text()
        for name in IMAGES:
            self.assertIn(f"docs/screenshots/{name}", readme)
            self.assertIn(f"v0.1.0-beta.1/docs/screenshots/{name}", notes)
        self.assertLess(readme.index("## Screenshots"), readme.index("## Features"))
        self.assertIn("**beta prerelease**", notes)
        self.assertIn("0.1.0b1", notes)
        self.assertIn("Wayland is unsupported", notes)
