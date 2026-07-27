from datetime import datetime

import streamlit as st

from api_client import ApiClientError, api_post
from cache import clear_health_caches
from config import USER_IDS, USER_LABELS
from form_components import render_measurement_inputs
from payloads import build_create_payload
from time_utils import JST


def render_create():
    st.subheader("新規登録")

    with st.form("create_form"):
        c1, c2 = st.columns(2)
        with c1:
            form_user = st.selectbox(
                "ユーザー *",
                options=USER_IDS,
                format_func=lambda x: USER_LABELS[x],
            )
            form_date = st.date_input("日付 *", value=datetime.now(JST).date())
        measurements = render_measurement_inputs("create", "create", left_col=c1, right_col=c2)
        form_memo = st.text_input("メモ", value="")
        form_meal_detail  = st.text_area("食事ログ", value="")
        form_activity_log = st.text_area("行動ログ", value="")

        submitted = st.form_submit_button("登録")

    if submitted:
        try:
            body = build_create_payload(
                user_id=form_user,
                form_date=form_date,
                measurements=measurements,
                memo=form_memo,
                meal_detail=form_meal_detail,
                activity_log=form_activity_log,
            )
        except ValueError as e:
            st.error(str(e))
            return

        try:
            result = api_post("/api/health/record", body)
        except ApiClientError as e:
            st.error(f"登録失敗: {e.message}" if e.status_code else f"API エラー: {e.message}")
            result = None
        if result:
            st.success("登録を受け付けました（反映には数秒かかる場合があります）")
            clear_health_caches()
            st.rerun()
