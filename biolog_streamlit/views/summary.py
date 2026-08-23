import streamlit as st

from api_client import ApiClientError
from cache import current_data_version, fetch_latest
from config import USER_IDS, USER_LABELS


def render_summary():
    st.subheader("直近データ — 家族全員")
    card_cols = st.columns(3)
    for i, uid in enumerate(USER_IDS):
        with card_cols[i]:
            st.markdown(f"### {USER_LABELS[uid]}")
            try:
                latest = fetch_latest(uid, current_data_version())
            except ApiClientError as e:
                st.error(f"API エラー: {e.message}")
                latest = None
            if latest:
                st.metric("体重",       f"{latest['weight']:.1f} kg"         if latest.get("weight")        is not None else "—")
                st.metric("体温",       f"{latest['temperature']:.1f} ℃"    if latest.get("temperature")  is not None else "—")
                st.metric("収縮期血圧", f"{latest['systolic_bp']} mmHg" if latest.get("systolic_bp") is not None else "—")
                st.metric("拡張期血圧", f"{latest['diastolic_bp']} mmHg" if latest.get("diastolic_bp") is not None else "—")
                st.metric("脈拍",       f"{latest['pulse']} bpm"         if latest.get("pulse")         is not None else "—")
                st.caption(f"最終更新: {latest['date']}")
            else:
                st.info("データなし")
