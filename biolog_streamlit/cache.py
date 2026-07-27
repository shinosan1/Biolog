import streamlit as st

from api_client import api_get


@st.cache_data(ttl=10)
def fetch_range_data(start: str, end: str):
    return api_get("/api/health/records/range", params={"start": start, "end": end})


@st.cache_data(ttl=10)
def fetch_latest(uid: str):
    return api_get(f"/api/health/records/latest/{uid}", suppress_404=True)


def clear_health_caches():
    fetch_latest.clear()
    fetch_range_data.clear()
