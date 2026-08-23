import time

import streamlit as st

from api_client import api_get


_DATA_VERSION_KEY = "data_version"


def current_data_version() -> int:
    """このセッションのキャッシュ世代番号を返す。

    初期値に `int(time.time())` を使うのは v1.5.7 の設計。0 から始めると、
    新しいセッションで過去セッションのキャッシュキー `(uid, 0)` に衝突し、
    古い値が再表示される（v1.5.5 で廃止した旧 version 機構の問題）。
    """
    if _DATA_VERSION_KEY not in st.session_state:
        st.session_state[_DATA_VERSION_KEY] = int(time.time())
    return st.session_state[_DATA_VERSION_KEY]


def bump_data_version() -> int:
    """書き込み成功時に世代を進め、以降の取得を新しいキャッシュキーへ移す。"""
    st.session_state[_DATA_VERSION_KEY] = current_data_version() + 1
    return st.session_state[_DATA_VERSION_KEY]


# version はキャッシュキーの一部としてだけ使う（関数本体では参照しない）。
@st.cache_data(ttl=10)
def fetch_range_data(start: str, end: str, version: int):
    return api_get("/api/health/records/range", params={"start": start, "end": end})


@st.cache_data(ttl=10)
def fetch_latest(uid: str, version: int):
    return api_get(f"/api/health/records/latest/{uid}", suppress_404=True)


def clear_health_caches():
    """書き込み成功時とサイドバー「更新」で呼ぶ。

    `.clear()` はプロセス全体のキャッシュを捨て、`bump_data_version()` は
    このセッションのキーを進める。両方を行うことで、他セッションが直後に
    詰め直した stale な値を、このセッションが拾い直すことを防ぐ。
    """
    fetch_latest.clear()
    fetch_range_data.clear()
    bump_data_version()
