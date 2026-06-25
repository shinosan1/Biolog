import requests

from config import API_BASE


class ApiClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _detail_from_http_error(e: requests.HTTPError) -> str:
    if not e.response:
        return str(e)
    try:
        return e.response.json().get("detail", str(e))
    except Exception:
        return str(e)


def api_get(path: str, params: dict = None, suppress_404: bool = False):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        if suppress_404 and r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        raise ApiClientError(_detail_from_http_error(e), e.response.status_code if e.response else None)


def api_post(path: str, body: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        raise ApiClientError(_detail_from_http_error(e), e.response.status_code if e.response else None)
    except Exception as e:
        raise ApiClientError(str(e))


def api_put(path: str, body: dict):
    try:
        r = requests.put(f"{API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        raise ApiClientError(_detail_from_http_error(e), e.response.status_code if e.response else None)
    except Exception as e:
        raise ApiClientError(str(e))


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        raise ApiClientError(_detail_from_http_error(e), e.response.status_code if e.response else None)
    except Exception as e:
        raise ApiClientError(str(e))
