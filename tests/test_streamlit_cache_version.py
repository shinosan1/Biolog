"""Regression tests for the read-cache version mechanism.

v1.5.7 で導入された `data_version` は、v1.6.0 の非破壊分割の際に廃止理由の記録なく
失われていた（v1.7.8 で復元）。同じ失われ方を検出できるよう、
実挙動とキャッシュキーへの受け渡しの両方を固定する。
"""

import inspect
import sys
import time
from pathlib import Path

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_DIR = PROJECT_ROOT / "biolog_streamlit"
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


_SCRIPT = (
    "import sys\n"
    f"sys.path.insert(0, {str(STREAMLIT_DIR)!r})\n"
    "import streamlit as st\n"
    "import cache\n"
    "\n"
    "cache.api_get = lambda *a, **k: None\n"
    "\n"
    "if 'log' not in st.session_state:\n"
    "    st.session_state['log'] = []\n"
    "st.session_state['log'].append(cache.current_data_version())\n"
    "\n"
    "if st.button('write'):\n"
    "    cache.clear_health_caches()\n"
    "    st.session_state['log'].append(cache.current_data_version())\n"
)


def _app() -> AppTest:
    app = AppTest.from_string(_SCRIPT, default_timeout=30)
    app.run()
    return app


def test_initial_version_is_seeded_from_the_clock_not_zero():
    app = _app()

    version = app.session_state["data_version"]

    assert isinstance(version, int)
    # 0 起点に戻すと、新しいセッションが過去セッションのキャッシュキーへ衝突する
    # （v1.5.5 で旧 version 機構を廃止した原因）。
    assert version > 1_600_000_000
    assert abs(version - int(time.time())) < 3600


def test_version_is_stable_until_a_write_happens():
    app = _app()
    first = app.session_state["data_version"]

    app.run()

    assert app.session_state["data_version"] == first
    assert set(app.session_state["log"]) == {first}


def test_clearing_caches_advances_the_version():
    app = _app()
    before = app.session_state["data_version"]

    app.button[0].click().run()

    after = app.session_state["data_version"]
    assert after == before + 1
    assert app.session_state["log"][-1] == after
    assert not app.exception


def test_cached_readers_take_version_as_part_of_the_cache_key():
    import cache

    for func in (cache.fetch_latest, cache.fetch_range_data):
        params = list(inspect.signature(func).parameters)
        assert params[-1] == "version", (func.__name__, params)


def test_cache_readers_are_called_with_the_current_version():
    summary = _read("biolog_streamlit/views/summary.py")
    graph = _read("biolog_streamlit/views/graph.py")

    assert "from cache import current_data_version, fetch_latest" in summary
    assert "fetch_latest(uid, current_data_version())" in summary

    assert "from cache import current_data_version, fetch_range_data" in graph
    assert "current_data_version()" in graph


def test_every_write_and_refresh_path_invalidates_the_cache():
    # clear_health_caches() が version を進めるため、この4箇所が invalidate の全経路。
    for relative_path in (
        "biolog_streamlit/streamlit_app.py",   # サイドバー「更新」
        "biolog_streamlit/views/create.py",    # 新規登録
        "biolog_streamlit/views/edit.py",      # 修正・削除
    ):
        assert "clear_health_caches()" in _read(relative_path), relative_path

    edit = _read("biolog_streamlit/views/edit.py")
    assert edit.count("clear_health_caches()") == 2  # 更新成功時と削除成功時


def test_clear_health_caches_keeps_both_invalidation_mechanisms():
    source = _read("biolog_streamlit/cache.py")

    # per-function clear（プロセス全体）と version（セッション単位）は併用する。
    assert "fetch_latest.clear()" in source
    assert "fetch_range_data.clear()" in source
    assert "bump_data_version()" in source
    assert "@st.cache_data(ttl=10)" in source
