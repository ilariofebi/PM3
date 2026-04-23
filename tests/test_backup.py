import json
import tempfile
import unittest
from pathlib import Path

from PM3.libs.pm3table import Pm3Database


class TestPm3Database(unittest.TestCase):
    def test_backup_creation_and_dedup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pm3_db.json"
            db_path.write_text(json.dumps({"pm3_procs": []}), encoding="utf-8")

            db = Pm3Database(db_path.as_posix())

            self.assertTrue(db.safe_write(lambda: True))
            backups = sorted(db.backup_dir.glob("pm3_db_*.json.gz"))
            self.assertEqual(len(backups), 1)

            self.assertTrue(db.safe_write(lambda: True))
            backups_after = sorted(db.backup_dir.glob("pm3_db_*.json.gz"))
            self.assertEqual(len(backups_after), 1)

    def test_cleanup_old_backups(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "pm3_db.json"
            db_path.write_text(json.dumps({"pm3_procs": []}), encoding="utf-8")
            db = Pm3Database(db_path.as_posix())
            db.max_backups = 2

            for idx in range(3):
                db_path.write_text(json.dumps({"pm3_procs": [idx]}), encoding="utf-8")
                self.assertTrue(db.safe_write(lambda: True))

            backups = sorted(db.backup_dir.glob("pm3_db_*.json.gz"))
            self.assertLessEqual(len(backups), 2)


if __name__ == "__main__":
    unittest.main()
