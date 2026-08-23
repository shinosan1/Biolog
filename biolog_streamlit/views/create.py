from datetime import datetime

import streamlit as st

from api_client import ApiClientError, api_post
from cache import clear_health_caches
from config import USER_IDS, USER_LABELS
from form_components import create_measurement_state_keys, render_measurement_inputs
from payloads import build_create_payload
from time_utils import JST


CREATE_KEY_PREFIX = "create"
CREATE_RESET_FLAG = "clear_create_form"

# 測定値以外の新規登録ウィジェットのキー。
CREATE_FIELD_KEYS = (
    "create_user_select",
    "create_date_input",
    "create_memo",
    "create_meal_detail",
    "create_activity_log",
)


def create_form_state_keys() -> tuple[str, ...]:
    """Session state keys held by every create form widget."""
    return create_measurement_state_keys(CREATE_KEY_PREFIX) + CREATE_FIELD_KEYS


def reset_create_form_state(session_state) -> None:
    """Clear the previous input, deferred to the run after a successful create.

    削除タブの clear_del_id と同じ deferred-clear 方式。ウィジェット生成前に
    呼ぶ必要がある。入力エラー・API エラー時はフラグが立たないため入力は残る。
    """
    if not session_state.get(CREATE_RESET_FLAG):
        return
    for key in create_form_state_keys():
        if key in session_state:
            del session_state[key]
    del session_state[CREATE_RESET_FLAG]


def render_create():
    st.subheader("新規登録")

    reset_create_form_state(st.session_state)

    with st.form("create_form"):
        c1, c2 = st.columns(2)
        with c1:
            form_user = st.selectbox(
                "ユーザー *",
                options=USER_IDS,
                format_func=lambda x: USER_LABELS[x],
                key="create_user_select",
            )
            form_date = st.date_input(
                "日付 *",
                value=datetime.now(JST).date(),
                key="create_date_input",
            )
        measurements = render_measurement_inputs(
            "create", CREATE_KEY_PREFIX, left_col=c1, right_col=c2
        )
        form_memo = st.text_input("メモ", value="", key="create_memo")
        form_meal_detail  = st.text_area("食事ログ", value="", key="create_meal_detail")
        form_activity_log = st.text_area("行動ログ", value="", key="create_activity_log")

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
            st.session_state[CREATE_RESET_FLAG] = True
            clear_health_caches()
            st.rerun()
