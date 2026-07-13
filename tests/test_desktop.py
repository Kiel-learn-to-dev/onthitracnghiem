import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from desktop import application_data_path, configure_database_path


class DesktopLauncherTests(unittest.TestCase):
    def test_uses_a_writable_per_user_database_instead_of_the_bundled_copy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            bundle_root = Path(temp_dir) / "bundle"
            bundled_database = bundle_root / "data" / "review.db"
            bundled_database.parent.mkdir(parents=True)
            bundled_database.write_bytes(b"sqlite data")
            app_data_root = Path(temp_dir) / "user-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(app_data_root)}, clear=False):
                database_path = configure_database_path(bundle_root)
                configured_path = os.environ["CSLT_DATABASE_PATH"]

            self.assertEqual(database_path, app_data_root / "CSLT-OnThi" / "data" / "review.db")
            self.assertEqual(database_path.read_bytes(), b"sqlite data")
            self.assertEqual(configured_path, str(database_path))

    def test_selects_platform_appropriate_application_data_roots(self):
        with patch.dict(os.environ, {"LOCALAPPDATA": "C:/Users/Test/AppData/Local"}, clear=False):
            self.assertEqual(application_data_path("win32"), Path("C:/Users/Test/AppData/Local") / "CSLT-OnThi")
        with patch.dict(os.environ, {"HOME": "/Users/test"}, clear=False):
            self.assertEqual(application_data_path("darwin"), Path("/Users/test") / "Library" / "Application Support" / "CSLT-OnThi")


if __name__ == "__main__":
    unittest.main()
