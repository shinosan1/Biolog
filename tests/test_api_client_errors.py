import importlib

import pytest
import requests


def _http_error(status_code, detail):
    response = requests.Response()
    response.status_code = status_code
    response._content = ('{"detail": "' + detail + '"}').encode()
    response.url = "http://localhost:8766/api/health/record"
    return requests.HTTPError(response=response)


def test_http_error_keeps_422_status_and_api_detail(monkeypatch):
    api_client = importlib.import_module("api_client")
    monkeypatch.setattr(api_client._SESSION, "post", lambda *args, **kwargs: (_ for _ in ()).throw(_http_error(422, "weight is invalid")))

    with pytest.raises(api_client.ApiClientError) as exc_info:
        api_client.api_post("/api/health/record", {})

    assert exc_info.value.status_code == 422
    assert exc_info.value.message == "weight is invalid"


@pytest.mark.parametrize("error_type", [requests.ConnectionError, requests.Timeout])
def test_get_connection_errors_become_api_client_errors(monkeypatch, error_type):
    api_client = importlib.import_module("api_client")
    def fail(*args, **kwargs):
        raise error_type("connection lost")
    monkeypatch.setattr(api_client._SESSION, "get", fail)

    with pytest.raises(api_client.ApiClientError) as exc_info:
        api_client.api_get("/api/health/records")

    assert exc_info.value.status_code is None
    assert exc_info.value.message == "connection lost"


@pytest.mark.parametrize("status", [404, 503])
def test_get_http_errors_keep_status_and_detail(monkeypatch, status):
    api_client = importlib.import_module("api_client")
    def fail(*args, **kwargs):
        raise _http_error(status, "server message")
    monkeypatch.setattr(api_client._SESSION, "get", fail)

    with pytest.raises(api_client.ApiClientError) as exc_info:
        api_client.api_get("/api/health/records")

    assert exc_info.value.status_code == status
    assert exc_info.value.message == "server message"
