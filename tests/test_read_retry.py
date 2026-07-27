import sqlite3
from contextlib import contextmanager

import pytest


def test_read_retries_locked_connection_without_exceeding_budget(
    temp_db_modules, monkeypatch
):
    _, biocore, _ = temp_db_modules
    attempts = []
    sleeps = []

    class Cursor:
        description = [("id",)]

        def fetchall(self):
            return [(1,)]

    class Connection:
        def execute(self, query, params):
            return Cursor()

    @contextmanager
    def sometimes_locked(*, read=False, write=False):
        attempts.append(read)
        if len(attempts) < 3:
            raise sqlite3.OperationalError("database is locked")
        yield Connection()

    monkeypatch.setattr(biocore, "get_connection", sometimes_locked)
    monkeypatch.setattr(biocore.time, "sleep", sleeps.append)

    assert biocore._execute_read("SELECT id FROM health_records") == [{"id": 1}]
    assert attempts == [True, True, True]
    assert sum(sleeps) == pytest.approx(0.3)
    assert sum(sleeps) < 10


def test_read_does_not_retry_non_lock_errors(temp_db_modules, monkeypatch):
    _, biocore, _ = temp_db_modules
    attempts = []

    @contextmanager
    def broken_connection(*, read=False, write=False):
        attempts.append(read)
        raise sqlite3.OperationalError("disk I/O error")
        yield

    monkeypatch.setattr(biocore, "get_connection", broken_connection)

    try:
        biocore._execute_read("SELECT 1")
    except sqlite3.OperationalError:
        pass
    else:
        raise AssertionError("non-lock error was swallowed")

    assert attempts == [True]
