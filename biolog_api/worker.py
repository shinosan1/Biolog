import json
import sqlite3
import time
from datetime import datetime, timezone
from queue import Queue

from db_manager import get_connection
from log_utils import mask_pii
from queue_manager import get_queue


def _log(op, request_id, queue_size, retry, status, extra=None):
    def safe(o):
        try:
            json.dumps(o)
            return o
        except Exception:
            return str(o)

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "op": op,
        "request_id": request_id,
        "queue_size": queue_size,
        "retry": retry,
        "status": status,
    }

    if extra:
        entry["extra"] = safe(extra)

    print(mask_pii(json.dumps(entry, ensure_ascii=False)), flush=True)

def worker_loop():
    q: Queue = get_queue()
    while True:
        task = q.get()

        if task is None:
            _log("shutdown", "", q.qsize(), 0, "stopping")
            q.task_done()
            break

        request_id = task.get("request_id", "")
        result_queue = task["result_queue"]

        try:
            result = _execute_with_retry(task, q)
            result_queue.put({"request_id": request_id, "status": "success", **result})
        except Exception as e:
            _log(task.get("operation", "?"), request_id, q.qsize(), 0, "error", {"error": str(e)})
            result_queue.put({"request_id": request_id, "status": "error", "error": str(e)})
        finally:
            q.task_done()


def _execute_with_retry(task: dict, q: Queue) -> dict:
    max_retry = 5
    delay = 0.1
    op = task.get("operation", "?")
    request_id = task.get("request_id", "")

    for attempt in range(max_retry):
        try:
            result = _execute_once(task)
            _log(op, request_id, q.qsize(), attempt, "success", result)
            return result
        except sqlite3.OperationalError as e:
            if "database is locked" not in str(e):
                raise
            _log(op, request_id, q.qsize(), attempt, "retry", {"error": str(e)})
            if attempt == max_retry - 1:
                raise
            time.sleep(delay)
            delay *= 2

    raise RuntimeError("unreachable")


def _execute_once(task: dict) -> dict:
    op = task["operation"]
    payload = task["payload"]
    _log(
    "worker_received",
    task.get("request_id", ""),
    0,
    0,
    "info",
    {"payload": task["payload"]}
)
    activity_log = payload.get("activity_log")

    if activity_log is None:
        _log(
            "activity_log_missing",
            task.get("request_id", ""),
            0,
            0,
            "warning",
            {"payload": payload}
        )
    with get_connection(write=True) as conn:
        if op == "insert":
            try:
                cur = conn.execute(
                    """
                    INSERT INTO health_records
                        (request_id, date, user_id, temperature, pulse,
                         systolic_bp, diastolic_bp, weight, body_fat,
                         muscle_mass, bmr, meal_detail, activity_log, memo)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        request_id   = excluded.request_id,
                        temperature  = excluded.temperature,
                        pulse        = excluded.pulse,
                        systolic_bp  = excluded.systolic_bp,
                        diastolic_bp = excluded.diastolic_bp,
                        weight       = excluded.weight,
                        body_fat     = excluded.body_fat,
                        muscle_mass  = excluded.muscle_mass,
                        bmr          = excluded.bmr,
                        meal_detail  = excluded.meal_detail,
                        activity_log = excluded.activity_log,
                        memo         = excluded.memo
                    """,
                    (
                        payload["request_id"],
                        payload["date"],
                        payload["user_id"],
                        payload.get("temperature"),
                        payload.get("pulse"),
                        payload.get("systolic_bp"),
                        payload.get("diastolic_bp"),
                        payload.get("weight"),
                        payload.get("body_fat"),
                        payload.get("muscle_mass"),
                        payload.get("bmr"),
                        payload.get("meal_detail"),
                        payload.get("activity_log"),
                        payload.get("memo", ""),
                    ),
                )
                return {"id": cur.lastrowid}
            except sqlite3.IntegrityError as e:
                if "request_id" in str(e).lower():
                    # DB責任: UNIQUE(request_id) 衝突 → SELECT で既存 id を返す（冪等）
                    row = conn.execute(
                        "SELECT id FROM health_records WHERE request_id = ?",
                        (payload["request_id"],),
                    ).fetchone()
                    return {"idempotent": True, "id": row[0] if row else None}
                raise  # CHECK 制約違反など他の IntegrityError はバブルアップ

        elif op == "update":
            record_id = payload["id"]
            _ALLOWED = {
                "temperature": float,
                "pulse": int,
                "systolic_bp": int,
                "diastolic_bp": int,
                "weight": float,
                "body_fat": float,
                "muscle_mass": float,
                "bmr": int,
                "memo": str,
                "activity_log": str,
                "meal_detail": str,
            }
            fields = {}
            for k, v in payload.items():
                if k == "id":
                    continue
                if k in _ALLOWED:
                    if v is None:
                        continue
                    try:
                        fields[k] = _ALLOWED[k](v)
                    except Exception:
                        raise ValueError(f"Invalid type for {k}: {v}")
            if not fields:
                raise ValueError("No fields to update")
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [record_id]
            print(json.dumps({
                "event": "UPDATE_SQL_EXECUTED",
                "record_id": record_id,
                "fields": list(fields.keys()),
            }, ensure_ascii=False), flush=True)
            cur = conn.execute(
                f"UPDATE health_records SET {set_clause} WHERE id = ?", values
            )
            if cur.rowcount == 0:
                raise ValueError(f"Record {record_id} not found")
            return {"id": record_id, "updated": cur.rowcount}

        elif op == "delete":
            record_id = payload["id"]
            cur = conn.execute(
                "DELETE FROM health_records WHERE id = ?", (record_id,)
            )
            if cur.rowcount == 0:
                raise ValueError(f"Record {record_id} not found")
            return {"id": record_id, "deleted": cur.rowcount}

        else:
            raise ValueError(f"Unknown operation: {op}")
