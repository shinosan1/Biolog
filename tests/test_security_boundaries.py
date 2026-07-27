import importlib
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "security_test.db"))
    for name in ("api", "worker", "write_repository", "db_manager", "biocore"):
        sys.modules.pop(name, None)


def test_api_has_no_cross_origin_middleware():
    api = importlib.import_module("api")
    assert all(
        middleware.cls.__name__ != "CORSMiddleware"
        for middleware in api.app.user_middleware
    )


def test_update_log_contains_fields_but_not_health_values(monkeypatch, capsys):
    api = importlib.import_module("api")
    monkeypatch.setattr(api, "_enqueue_and_wait", lambda operation, payload: {"id": 1})

    api.update_record(1, api.HealthRecordUpdate(weight=61.234, memo="private memo"))

    output = capsys.readouterr().out
    assert "weight" in output
    assert "memo" in output
    assert "61.234" not in output
    assert "private memo" not in output


def test_worker_log_contains_fields_but_not_health_values(monkeypatch, capsys):
    worker = importlib.import_module("worker")
    monkeypatch.setattr(worker, "insert_record", lambda payload: {"id": 1})

    worker._execute_once({
        "operation": "insert",
        "request_id": "request-private",
        "payload": {
            "weight": 61.234,
            "activity_log": "private activity",
            "memo": "private memo",
        },
    })

    output = capsys.readouterr().out
    assert "weight" in output
    assert "activity_log" in output
    assert "61.234" not in output
    assert "private activity" not in output
    assert "private memo" not in output


def test_chart_modules_have_no_debug_prints():
    streamlit_dir = Path(__file__).resolve().parents[1] / "biolog_streamlit"
    for relative_path in ("charts.py", "views/graph.py"):
        source = (streamlit_dir / relative_path).read_text(encoding="utf-8")
        assert "print(" not in source


def test_api_client_rejects_nonlocal_urls_and_ignores_environment_proxy():
    api_client = importlib.import_module("api_client")
    assert api_client._SESSION.trust_env is False
    assert api_client._validated_api_base("http://biolog-api:8766") == "http://biolog-api:8766"
    assert api_client._validated_api_base("http://localhost:8766/") == "http://localhost:8766"
    with pytest.raises(ValueError):
        api_client._validated_api_base("https://example.com")
    with pytest.raises(ValueError):
        api_client._validated_api_base("http://example.com")
