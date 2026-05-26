MIGRATION_ID = "001"
DESCRIPTION = "create health_records table, add columns and indexes"

_DDL_CREATE = [
    """
    CREATE TABLE IF NOT EXISTS health_records (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id   TEXT    NOT NULL UNIQUE,
        date         TEXT    NOT NULL,
        user_id      TEXT    NOT NULL,
        temperature  REAL,
        pulse        INTEGER,
        systolic_bp  INTEGER,
        diastolic_bp INTEGER,
        weight       REAL,
        body_fat     REAL,
        muscle_mass  REAL,
        bmr          INTEGER,
        meal_detail  TEXT,
        activity_log TEXT,
        memo         TEXT    NOT NULL DEFAULT '',
        created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,
]

_DDL_MIGRATE = [
    "ALTER TABLE health_records ADD COLUMN request_id   TEXT",
    "ALTER TABLE health_records ADD COLUMN meal_detail  TEXT",
    "ALTER TABLE health_records ADD COLUMN activity_log TEXT",
]

_DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_hr_user_date ON health_records(user_id, date DESC)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uidx_hr_user_date ON health_records(user_id, date)",
]


def run(conn):
    # commit/rollback は runner が管理する。conn.commit() は呼ばない。
    # CREATE TABLE と ALTER TABLE は環境差吸収のため両方残す（削除・統合禁止）。

    for stmt in _DDL_CREATE:
        conn.execute(stmt)

    for stmt in _DDL_MIGRATE:
        try:
            conn.execute(stmt)
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                pass
            else:
                raise

    for stmt in _DDL_INDEXES:
        conn.execute(stmt)
