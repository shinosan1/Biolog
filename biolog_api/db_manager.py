import os
import sqlite3
from contextlib import contextmanager

DATABASE_PATH = os.getenv("DATABASE_PATH")

if not DATABASE_PATH:
    raise RuntimeError("DATABASE_PATH is not set")


@contextmanager
def get_connection(*, read: bool = False, write: bool = False):
    if read == write:
        raise ValueError("Specify exactly one of read=True or write=True")

    conn = sqlite3.connect(
        DATABASE_PATH,
        timeout=0,
        isolation_level=None,
    )
    conn.text_factory = str
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")

        if write:
            conn.execute("BEGIN IMMEDIATE")

        yield conn

        if write:
            conn.commit()

    except Exception:
        if write:
            conn.rollback()
        raise

    finally:
        conn.close()
