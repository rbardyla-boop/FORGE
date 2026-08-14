import tempfile
import unittest
from pathlib import Path

from forge_core.ds_d0r import artifact_manifest


class DsD0RHelpersTest(unittest.TestCase):
    def test_artifact_manifest_excludes_upload_manifest_from_public_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text("index\n")
            (root / "research").mkdir()
            (root / "research/index.html").write_text("research\n")
            (root / "_UPLOAD_MANIFEST.json").write_text("{}\n")
            manifest = artifact_manifest(root)
            self.assertEqual(manifest["file_count"], 2)
            self.assertTrue(manifest["manifest_file_present"])
            self.assertEqual(manifest["ds00_files_present"], [])
            self.assertEqual(len(manifest["artifact_sha256"]), 64)

    def test_artifact_manifest_reports_ds00_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "digital-stewardship-00.html").write_text("private\n")
            manifest = artifact_manifest(root)
            self.assertEqual(manifest["ds00_files_present"], ["digital-stewardship-00.html"])


if __name__ == "__main__":
    unittest.main()
