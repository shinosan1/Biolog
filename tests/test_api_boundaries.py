import asyncio
import importlib
import sys

import pytest
from fastapi import HTTPException
from pydantic import ValidationError


def _load_api(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "unused.db"))
    for name in ("api", "worker", "write_repository", "db_manager", "biocore"):
        sys.modules.pop(name, None)
    return importlib.import_module("api")


def test_biocore_rejects_negative_or_unbounded_pagination(temp_db_modules):
    _, biocore, _ = temp_db_modules

    for limit, offset in ((-1, 0), (0, 0), (501, 0), (20, -1), (20, 10001)):
        with pytest.raises(ValueError):
            biocore.get_health_records(limit=limit, offset=offset)


def test_create_schema_rejects_invalid_dates_and_oversized_text():
    schemas = importlib.import_module("schemas")
    base = {
        "request_id": "r",
        "date": "2026-02-28",
        "user_id": "self",
        "weight": 60,
    }

    with pytest.raises(ValidationError):
        schemas.HealthRecordCreate(**{**base, "date": "2026-02-30"})
    with pytest.raises(ValidationError):
        schemas.HealthRecordCreate(**{**base, "request_id": "x" * 129})
    with pytest.raises(ValidationError):
        schemas.HealthRecordCreate(**{**base, "memo": "x" * 10001})


def test_range_rejects_invalid_or_reversed_dates(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)

    for start, end in (("2026-02-30", "2026-03-01"), ("2026-03-02", "2026-03-01")):
        with pytest.raises(HTTPException) as exc:
            api.records_by_range(start, end)
        assert exc.value.status_code == 422


def test_create_rejects_non_object_and_invalid_json(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)

    class RequestValue:
        async def json(self):
            return ["not", "an", "object"]

    class BrokenRequest:
        async def json(self):
            raise ValueError("invalid json")

    for request in (RequestValue(), BrokenRequest()):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(api.create_record(request))
        assert exc.value.status_code == 422


def test_create_rejects_non_numeric_integer_fields(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)

    class PayloadRequest:
        def __init__(self, payload):
            self._payload = payload

        async def json(self):
            return self._payload

    # "1e309" と "inf" は float() を通過し int() で OverflowError になる。
    # OverflowError は ValueError の派生ではないため、捕捉漏れがあると
    # 422 ではなく 500 になる。
    for field in ("pulse", "bmr", "systolic_bp", "diastolic_bp"):
        for value in ("abc", "inf", "1e309"):
            request = PayloadRequest({
                "request_id": "rid",
                "date": "2026-06-25",
                "user_id": "self",
                "weight": 61.2,
                field: value,
            })

            with pytest.raises(HTTPException) as exc:
                asyncio.run(api.create_record(request))

            assert exc.value.status_code == 422
            assert field in exc.value.detail


def test_create_accepts_float_valued_integer_fields(tmp_path, monkeypatch):
    api = _load_api(tmp_path, monkeypatch)
    enqueued = {}

    def _fake_enqueue(operation, payload):
        enqueued["operation"] = operation
        enqueued["payload"] = payload
        return {"status": "success", "id": 1}

    monkeypatch.setattr(api, "_enqueue_and_wait", _fake_enqueue)

    class PayloadRequest:
        async def json(self):
            return {
                "request_id": "rid",
                "date": "2026-06-25",
                "user_id": "self",
                "pulse": 72.9,
                "bmr": "1400.0",
            }

    asyncio.run(api.create_record(PayloadRequest()))

    assert enqueued["operation"] == "insert"
    assert enqueued["payload"]["pulse"] == 72
    assert enqueued["payload"]["bmr"] == 1400
