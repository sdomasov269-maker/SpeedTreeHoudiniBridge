import tempfile
import unittest
import zipfile
from pathlib import Path
from tools.build_release import build_release


class ReleaseTests(unittest.TestCase):
    def test_archive_is_installable_and_excludes_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            first = build_release(Path(directory) / "first.zip")
            second = build_release(Path(directory) / "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertIsNone(archive.testzip())
                names = archive.namelist()
                self.assertTrue(any(n.endswith("/install_houdini.py") for n in names))
                self.assertTrue(any(n.endswith("/houdini/toolbar/speedtree_bridge.shelf") for n in names))
                self.assertFalse(any(n.endswith((".hip", ".json", ".pyc", ".log")) for n in names))
                self.assertFalse(any("__pycache__" in n or "/tests/" in n for n in names))
                self.assertFalse(any(n.endswith(('/live_bridge.py', '/live_ui.py', '/Start Live Bridge.cmd', '/Start Live Bridge.sh')) for n in names))
                launcher = next(n for n in names if n.endswith("/Start Bridge.sh"))
                self.assertTrue(archive.getinfo(launcher).external_attr >> 16 & 0o111)
