"""Create and restore consistent SQLite backups without copying a live file directly."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def _copy_sqlite(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Không tìm thấy database nguồn: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def backup_database(source: Path, destination: Path) -> None:
    """Write a transactionally consistent backup of a SQLite database."""
    _copy_sqlite(source, destination)


def restore_database(backup: Path, destination: Path) -> None:
    """Restore a backup by SQLite's backup API, preserving a valid destination file."""
    _copy_sqlite(backup, destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup or restore a SQLite database")
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.action == "backup":
        backup_database(args.source, args.destination)
    else:
        restore_database(args.source, args.destination)
    print(args.destination)


if __name__ == "__main__":
    main()
