"""
Migration runner for BioLog.

Usage:
    docker exec biolog-api python migrations/runner.py
    DATABASE_PATH=/path/to/biolog.db python migrations/runner.py
"""

import importlib.util
import os
import re
import sqlite3
from pathlib import Path

DATABASE_PATH = os.getenv("DATABASE_PATH")
if not DATABASE_PATH:
    raise RuntimeError("DATABASE_PATH is not set")

_VERSIONS_DIR = Path(__file__).parent / "versions"

_CREATE_MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id         TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def _get_applied(conn):
    conn.execute(_CREATE_MIGRATIONS_TABLE)
    rows = conn.execute("SELECT id FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def _acquire_lock():
    """Return True if lock acquired, False if already locked."""
    conn = sqlite3.connect(DATABASE_PATH, isolation_level=None)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS migration_lock (
            id        INTEGER PRIMARY KEY CHECK (id = 1),
            locked_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    row = conn.execute(
        "SELECT locked_at FROM migration_lock WHERE id = 1"
    ).fetchone()
    if row:
        print(f"Migration lock exists (locked_at: {row[0]}).")
        print("If stale, remove manually: DELETE FROM migration_lock WHERE id = 1")
        conn.close()
        return False
    try:
        conn.execute("INSERT INTO migration_lock (id) VALUES (1)")
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def _release_lock():
    conn = sqlite3.connect(DATABASE_PATH, isolation_level=None)
    conn.execute("DELETE FROM migration_lock WHERE id = 1")
    conn.close()


def _extract_id(path):
    m = re.match(r"migrate_(\d+)", path.stem)
    return int(m.group(1)) if m else 999999


def _load_versions():
    paths = sorted(_VERSIONS_DIR.glob("migrate_*.py"), key=_extract_id)
    modules = []
    for path in paths:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        modules.append(mod)
    return modules


def run_all():
    if not _acquire_lock():
        return

    try:
        conn = sqlite3.connect(DATABASE_PATH, isolation_level=None)
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")

        applied = _get_applied(conn)
        versions = _load_versions()
        pending = [m for m in versions if m.MIGRATION_ID not in applied]

        if not pending:
            print("All migrations already applied.")
            conn.close()
            return

        for mod in pending:
            mid = mod.MIGRATION_ID
            desc = getattr(mod, "DESCRIPTION", "")
            print(f"[{mid}] Applying: {desc}")

            try:
                conn.execute("BEGIN IMMEDIATE")
                mod.run(conn)
                conn.execute(
                    "INSERT INTO schema_migrations (id) VALUES (?)", (mid,)
                )
                conn.commit()
                print(f"[{mid}] Done.")
            except Exception:
                conn.rollback()
                raise

        print(f"\n{len(pending)} migration(s) applied.")
        conn.close()

    finally:
        _release_lock()


if __name__ == "__main__":
    run_all()
