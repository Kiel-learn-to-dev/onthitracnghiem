import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.backup_database import backup_database, restore_database
from scripts.storage import create_database


class BackupDatabaseTests(unittest.TestCase):
    def test_restores_a_consistent_sqlite_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.db"
            backup = root / "backup.db"
            restored = root / "restored.db"
            create_database(source)
            connection = sqlite3.connect(source)
            connection.execute("INSERT INTO sources (filename, kind, checksum) VALUES ('sample.xlsx', 'xlsx', 'a')")
            connection.commit()
            connection.close()

            backup_database(source, backup)
            restore_database(backup, restored)

            restored_connection = sqlite3.connect(restored)
            try:
                self.assertEqual(restored_connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0], 1)
            finally:
                restored_connection.close()


if __name__ == "__main__":
    unittest.main()
