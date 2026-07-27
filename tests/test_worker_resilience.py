import importlib
import sys
import threading
from queue import Empty, Queue

import pytest
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def api_import_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "unused.db"))
    for name in ("api", "worker", "write_repository", "db_manager", "biocore"):
        sys.modules.pop(name, None)


def _start_isolated_worker(monkeypatch):
    worker = importlib.import_module("worker")
    task_queue = Queue()
    monkeypatch.setattr(worker, "get_queue", lambda: task_queue)
    thread = threading.Thread(target=worker.worker_loop, daemon=True)
    thread.start()
    return worker, task_queue, thread


def _submit(task_queue, operation, payload):
    result_queue = Queue()
    task_queue.put({
        "operation": operation,
        "request_id": payload.get("request_id", "test-request"),
        "payload": payload,
        "result_queue": result_queue,
    })
    return result_queue.get(timeout=2)


def test_missing_update_does_not_stop_worker(monkeypatch):
    worker, task_queue, thread = _start_isolated_worker(monkeypatch)
    monkeypatch.setattr(
        worker, "update_record",
        lambda payload: (_ for _ in ()).throw(ValueError("Record 999 not found")),
    )

    result = _submit(task_queue, "update", {"id": 999})

    assert result["error_kind"] == "not_found"
    assert thread.is_alive()
    task_queue.put(None)
    thread.join(timeout=2)


def test_missing_delete_allows_next_insert(monkeypatch):
    worker, task_queue, thread = _start_isolated_worker(monkeypatch)
    monkeypatch.setattr(
        worker, "delete_record",
        lambda payload: (_ for _ in ()).throw(ValueError("Record 999 not found")),
    )
    monkeypatch.setattr(worker, "insert_record", lambda payload: {"id": 1})

    failed = _submit(task_queue, "delete", {"id": 999})
    succeeded = _submit(task_queue, "insert", {"request_id": "next"})

    assert failed["error_kind"] == "not_found"
    assert succeeded["status"] == "success"
    assert thread.is_alive()
    task_queue.put(None)
    thread.join(timeout=2)


def test_enqueue_maps_worker_error_kinds(monkeypatch):
    api = importlib.import_module("api")

    class ResultQueue:
        def __init__(self, result):
            self.result = result

        def get(self, timeout):
            return self.result

    for error_kind, expected_status in (("not_found", 404), ("validation", 422)):
        monkeypatch.setattr(
            api,
            "SyncQueue",
            lambda result={"status": "error", "error_kind": error_kind, "error": "safe"}:
                ResultQueue(result),
        )
        with pytest.raises(HTTPException) as exc:
            api._enqueue_and_wait("update", {"id": 999})
        assert exc.value.status_code == expected_status


def test_enqueue_timeout_returns_503(monkeypatch):
    api = importlib.import_module("api")

    class UnresponsiveQueue:
        def get(self, timeout):
            raise Empty

    monkeypatch.setattr(api, "SyncQueue", UnresponsiveQueue)

    with pytest.raises(HTTPException) as exc:
        api._enqueue_and_wait("insert", {"request_id": "timeout"})

    assert exc.value.status_code == 503
    assert "did not respond" in exc.value.detail
