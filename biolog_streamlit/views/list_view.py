import pandas as pd
import streamlit as st

from api_client import ApiClientError, api_get
from config import USER_LABELS
from formatters import _safe_str, is_truncated, truncate
from time_utils import to_jst


def render_list(selected_users: list, date_start, date_end):
    st.subheader("データ一覧")

    page = st.number_input("ページ", min_value=1, value=1, step=1)
    page_size = 20
    offset = (page - 1) * page_size

    params = {"limit": page_size, "offset": offset}
    if len(selected_users) == 1:
        params["user_id"] = selected_users[0]

    try:
        records = api_get("/api/health/records", params=params)
    except ApiClientError as e:
        st.error(f"API エラー: {e.message}")
        records = None
    if records:
        df = pd.DataFrame(records)
        df["ユーザー"] = df["user_id"].map(USER_LABELS)
        display_cols = [
            "id", "date", "ユーザー", "created_at",
            "temperature", "pulse", "systolic_bp", "diastolic_bp",
            "weight", "body_fat", "muscle_mass", "bmr",
            "meal_detail", "activity_log", "memo",
        ]
        existing = [c for c in display_cols if c in df.columns]
        disp = df[existing].copy()
        if "created_at" in disp.columns:
            disp["created_at"] = disp["created_at"].apply(to_jst)
        disp = disp.rename(columns={
            "created_at":   "記録日時",
            "date":         "対象日",
            "weight":       "体重(kg)",
            "systolic_bp":  "収縮期血圧",
            "diastolic_bp": "拡張期血圧",
            "temperature":  "体温(℃)",
            "pulse":        "脈拍(bpm)",
            "body_fat":     "体脂肪率(%)",
            "muscle_mass":  "筋肉量(kg)",
            "bmr":          "基礎代謝(kcal)",
            "memo":         "メモ",
            "meal_detail":  "食事ログ",
            "activity_log": "行動ログ",
        })
        priority = [
            "id",
            "ユーザー",
            "対象日",
            "記録日時",
            "体重(kg)",
            "収縮期血圧",
            "拡張期血圧",
            "体温(℃)",
            "脈拍(bpm)",
            "基礎代謝(kcal)",
            "体脂肪率(%)",
            "筋肉量(kg)",
            "メモ",
            "食事ログ",
            "行動ログ",
        ]
        ordered = [c for c in priority if c in disp.columns]
        rest = [c for c in disp.columns if c not in ordered]
        disp = disp[ordered + rest]

        # CSV用: 完全データ（省略なし）
        disp_csv = disp.copy()

        # 表示用: 長文列を省略
        _LIMITS = {
            "メモ":    40,
            "食事ログ": 80,
            "行動ログ": 200,
        }
        disp_view = disp.copy()
        for col, limit in _LIMITS.items():
            if col in disp_view.columns:
                disp_view[col] = disp_view[col].apply(
                    lambda s, lim=limit: truncate(s, lim)
                )

        st.dataframe(disp_view, use_container_width=True)

        # ─── 詳細表示（_LIMITS を超えるセルのみ expander 展開）───
        long_cols = [c for c in _LIMITS if c in disp.columns]
        has_date = "対象日" in disp.columns
        has_user = "ユーザー" in disp.columns
        shown_any = False
        for idx, _row in disp.iterrows():
            expanders_for_row = []
            for col in long_cols:
                full = _safe_str(disp.at[idx, col])
                if is_truncated(full, _LIMITS[col]):
                    expanders_for_row.append((col, full))
            if not expanders_for_row:
                continue
            if not shown_any:
                st.divider()
                st.caption("全文表示（省略された長文のみ）")
                shown_any = True
            label_date = _safe_str(disp.at[idx, "対象日"]) if has_date else ""
            label_user = _safe_str(disp.at[idx, "ユーザー"]) if has_user else ""
            for col, full in expanders_for_row:
                with st.expander(f"{label_date} / {label_user} / {col}"):
                    st.write(full)

        csv = disp_csv.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="CSV ダウンロード",
            data=csv,
            file_name=f"biolog_{date_start}_{date_end}.csv",
            mime="text/csv",
        )
    else:
        st.info("データがありません")
