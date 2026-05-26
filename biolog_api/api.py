import json
import os
import signal
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from queue import Queue as SyncQueue
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import biocore
import preprocess as pp
from db_manager import get_connection
from log_utils import mask_pii
from queue_manager import get_queue
from schemas import HealthRecordCreate, HealthRecordUpdate
from worker import worker_loop
DATABASE_PATH = os.getenv("DATABASE_PATH", "")

_worker_thread: Optional[threading.Thread] = None


def _start_worker() -> threading.Thread:
    t = threading.Thread(target=worker_loop, daemon=True, name="biolog-worker")
    t.start()
    return t


def _stop_worker(t: threading.Thread):
    get_queue().put(None)
    t.join(timeout=10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_thread

    _worker_thread = _start_worker()

    def _handle_sigterm(signum, frame):
        if _worker_thread:
            _stop_worker(_worker_thread)

    signal.signal(signal.SIGTERM, _handle_sigterm)

    yield

    if _worker_thread:
        _stop_worker(_worker_thread)


app = FastAPI(title="BioLog API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _enqueue_and_wait(operation: str, payload: dict) -> dict:
    result_q: SyncQueue = SyncQueue()
    task = {
        "operation": operation,
        "request_id": payload.get("request_id", ""),
        "payload": payload,
        "result_queue": result_q,
    }
    q = get_queue()
    if q.full():
        raise HTTPException(status_code=503, detail="Write queue is full, try again later")
    q.put(task)
    result = result_q.get(timeout=30)
    if result["status"] == "error":
        detail = result.get("error", "Worker error")
        if "not found" in detail:
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=500, detail=detail)
    return result


@app.get("/api/health/health")
def health_check():
    return {"status": "ok", "db": DATABASE_PATH}


@app.post("/api/health/record", status_code=201)
async def create_record(request: Request):
    raw = await request.json()
    rid = raw.get("request_id", "?")

    # ---- logging wrapper ----
    def log(obj):
        print(mask_pii(json.dumps(obj, ensure_ascii=False)), flush=True)
    # ------------------------

    log({"event": "REQ_START", "request_id": rid})
    log({"event": "API_IN", "fields": list(raw.keys())})

    preprocessed = pp.preprocess_record(raw)
    generated = [k for k in ("request_id", "date") if not raw.get(k)]

    if generated:
        log({"event": "API_ENRICH", "generated": generated})

    log({"event": "PREPROCESS", "request_id": preprocessed.get("request_id")})

    known = set(HealthRecordCreate.model_fields.keys())
    unknown = set(preprocessed.keys()) - known

    if unknown:
        log({"event": "UNKNOWN_KEYS", "keys": sorted(unknown)})

    try:
        record = HealthRecordCreate(**preprocessed)
    except Exception as e:
        log({
            "event": "VALIDATION",
            "status": "error",
            "endpoint": "/api/health/record",
            "detail": str(e),
            "payload": preprocessed,
        })
        raise HTTPException(status_code=422, detail=str(e))

    log({"event": "VALIDATION", "status": "ok"})

    payload = record.model_dump()

    log({
        "event": "API_PAYLOAD_KEYS",
        "keys": list(payload.keys())
    })

    log({
        "event": "API_PAYLOAD_BEFORE_QUEUE",
        "payload": payload
    })

    log({
        "event": "DB_WRITE",
        "request_id": payload["request_id"]
    })

    result = _enqueue_and_wait("insert", payload)

    log({
        "event": "REQ_END",
        "request_id": payload["request_id"],
        "status": "ok"
    })

    return {"message": "登録完了", **result}

@app.put("/api/health/record/{record_id}")
def update_record(record_id: int, record: HealthRecordUpdate):
    payload = {"id": record_id, **record.model_dump(exclude_unset=True)}
    print(json.dumps({
        "event": "UPDATE_REQUEST",
        "record_id": record_id,
        "payload": {k: v for k, v in payload.items() if k != "id"},
    }, ensure_ascii=False), flush=True)
    result = _enqueue_and_wait("update", payload)
    return {"message": "更新完了", **result}


@app.get("/api/health/record/day")
def get_record_by_day(user_id: str, date: str):
    record = biocore.get_record_by_user_date(user_id, date)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.get("/api/health/record/{record_id}")
def get_record(record_id: int):
    record = biocore.get_record_by_id(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return record


@app.delete("/api/health/record/{record_id}")
def delete_record(record_id: int):
    payload = {"id": record_id}
    result = _enqueue_and_wait("delete", payload)
    return {"message": "削除完了", **result}


@app.get("/api/health/records")
def list_records(
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    try:
        return biocore.get_health_records(user_id=user_id, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health/records/range")
def records_by_range(
    start: str,
    end: str,
    user_id: Optional[str] = None,
):
    try:
        return biocore.get_health_records_by_date_range(
            start_date=start, end_date=end, user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/health/records/latest/{user_id}")
def latest_record(user_id: str):
    record = biocore.get_latest_record(user_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No records for user_id={user_id}")
    return record
