import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from backup_engine import KodiBackupEngine


CLEANUP_OFF = {
    "thumbnails": False,
    "tmdb_blur": False,
    "tmdb_crop": False,
    "addon_packages": False,
    "tmdb_database": False,
    "umbrella_cache": False,
    "umbrella_search": False,
    "cocoscrapers_cache": False,
}


class KodiBackupEngineTests(unittest.TestCase):
    def test_backup_rejects_userdata_and_addons_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            kodi = base / "kodi"
            backup = base / "backup"
            kodi.mkdir()
            backup.mkdir()
            (kodi / "userdata").write_text("not a directory", encoding="utf-8")
            (kodi / "addons").write_text("not a directory", encoding="utf-8")

            result = KodiBackupEngine(lambda _: None).perform_full_backup(
                str(kodi), str(backup), "", None, CLEANUP_OFF
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["error_message"], "Invalid Kodi directory")
            self.assertEqual(list(backup.iterdir()), [])

    def test_backup_warns_when_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            kodi = base / "kodi"
            backup = base / "backup"
            (kodi / "userdata").mkdir(parents=True)
            (kodi / "addons").mkdir()
            (kodi / "userdata" / "ok.txt").write_text("ok", encoding="utf-8")
            skipped = kodi / "userdata" / "skip.txt"
            skipped.write_text("skip", encoding="utf-8")
            backup.mkdir()

            original_write = zipfile.ZipFile.write

            def write_or_skip(zip_file, filename, arcname=None, *args, **kwargs):
                if Path(filename) == skipped:
                    raise OSError("simulated locked file")
                return original_write(zip_file, filename, arcname, *args, **kwargs)

            with patch.object(zipfile.ZipFile, "write", write_or_skip):
                result = KodiBackupEngine(lambda _: None).perform_full_backup(
                    str(kodi), str(backup), "", None, CLEANUP_OFF
                )

            self.assertTrue(result["success"])
            self.assertEqual(result["skipped_files_count"], 1)
            self.assertTrue(result["warning_message"])

    def test_restore_fails_when_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            backup_zip = base / "conflict.zip"
            with zipfile.ZipFile(backup_zip, "w") as z:
                z.writestr("userdata/conflict", "file first")
                z.writestr("userdata/conflict/nested.txt", "cannot write under existing file")
                z.writestr("addons/good.txt", "a")

            result = KodiBackupEngine(lambda _: None).perform_restore(
                str(backup_zip), str(base / "restore-target")
            )

            self.assertFalse(result["success"])
            self.assertEqual(result["error_message"], "Failed to extract backup archive")

    def test_restore_rejects_zip_slip_entry(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            backup_zip = base / "bad.zip"
            with zipfile.ZipFile(backup_zip, "w") as z:
                z.writestr("userdata/good.txt", "u")
                z.writestr("addons/good.txt", "a")
                z.writestr("../escape.txt", "x")

            result = KodiBackupEngine(lambda _: None).perform_restore(
                str(backup_zip), str(base / "target")
            )

            self.assertFalse(result["success"])
            self.assertIn("Unsafe zip entry", result["error_message"])
            self.assertFalse((base / "escape.txt").exists())

    def test_restore_rejects_non_empty_non_kodi_target(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            backup_zip = base / "good.zip"
            with zipfile.ZipFile(backup_zip, "w") as z:
                z.writestr("userdata/good.txt", "u")
                z.writestr("addons/good.txt", "a")
            target = base / "target"
            target.mkdir()
            (target / "unrelated.txt").write_text("keep", encoding="utf-8")

            result = KodiBackupEngine(lambda _: None).perform_restore(str(backup_zip), str(target))

            self.assertFalse(result["success"])
            self.assertTrue((target / "unrelated.txt").exists())


if __name__ == "__main__":
    unittest.main()
