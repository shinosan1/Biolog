import importlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from queue import Queue


class _ThreadState:
    def __init__(self, alive):
        self._alive = alive

    def is_alive(self):
        return self._alive


def _load_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "unused.db"))
    for name in ("api", "worker", "write_repository", "db_manager", "biocore"):
        sys.modules.pop(name, None)
    return importlib.import_module("api")


def test_healthcheck_reports_ok_without_database_path(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)
    monkeypatch.setattr(api, "_worker_thread", _ThreadState(True))
    monkeypatch.setattr(api.biocore, "check_database", lambda: True)
    monkeypatch.setattr(api, "get_queue", lambda: Queue(maxsize=100))

    result = api.health_check()

    assert result["status"] == "ok"
    assert result["worker_alive"] is True
    assert result["database_ok"] is True
    assert "db" not in result
    assert str(tmp_path) not in str(result)


def test_healthcheck_reports_unhealthy_when_worker_stops(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)
    monkeypatch.setattr(api, "_worker_thread", _ThreadState(False))
    monkeypatch.setattr(api.biocore, "check_database", lambda: True)

    assert api.health_check()["status"] == "unhealthy"


def test_database_check_is_read_only(temp_db_modules):
    _, biocore, db_path = temp_db_modules
    before = db_path.read_bytes()

    assert biocore.check_database() is True
    assert db_path.read_bytes() == before


def test_database_check_rejects_empty_database(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)
    monkeypatch.setattr(api, "_worker_thread", _ThreadState(True))

    assert api.biocore.check_database() is False
    assert api.health_check()["status"] == "unhealthy"


def test_database_check_rejects_missing_required_migration(temp_db_modules):
    _, biocore, db_path = temp_db_modules
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM schema_migrations WHERE id = '002'")

    assert biocore.check_database() is False


def test_database_check_rejects_missing_core_table(temp_db_modules):
    _, biocore, db_path = temp_db_modules
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE request_history")

    assert biocore.check_database() is False


def test_migration_lock_stops_entrypoint_before_api_start(tmp_path):
    db_path = tmp_path / "locked.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE migration_lock (id INTEGER PRIMARY KEY, locked_at TEXT)")
        conn.execute("INSERT INTO migration_lock VALUES (1, '2026-09-30')")

    api_dir = Path(__file__).resolve().parents[1] / "biolog_api"
    result = subprocess.run(
        [sys.executable, str(api_dir / "migrations" / "runner.py")],
        env={**os.environ, "DATABASE_PATH": str(db_path)},
        capture_output=True, text=True, check=False,
    )

    assert result.returncode != 0
    assert "Migration lock is already held" in result.stderr
    entrypoint = (api_dir / "entrypoint.sh").read_text(encoding="utf-8")
    assert "set -e" in entrypoint
    assert entrypoint.index("python migrations/runner.py") < entrypoint.index("exec uvicorn")


def test_metadata_endpoint_returns_database_specific_legacy_boundary(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)
    monkeypatch.setattr(api.biocore, "get_metadata_value", lambda key: "0")

    assert api.health_metadata() == {"legacy_utc_max_record_id": 0}
