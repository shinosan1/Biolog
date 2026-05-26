import os
import time
import uuid
from time_utils import to_jst, JST
from datetime import date, timedelta, datetime

import japanize_matplotlib  # import するだけで日本語フォント有効化
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import requests
import seaborn as sns
import streamlit as st

API_BASE = os.getenv("BIOLOG_API_URL", "http://localhost:8766")

USER_LABELS = {"self": "自分", "father": "父", "mother": "母"}
USER_IDS = list(USER_LABELS.keys())
USER_COLORS = {"self": "#1f77b4", "father": "#2ca02c", "mother": "#d62728"}

plt.style.use("dark_background")

st.set_page_config(page_title="BioLog", layout="wide")
st.title("BioLog — 家族健康記録")


@st.cache_data
def fetch_range_data(start: str, end: str):
    return api_get("/api/health/records/range", params={"start": start, "end": end})


@st.cache_data
def fetch_latest(uid: str):
    return api_get(f"/api/health/records/latest/{uid}", suppress_404=True)


def _jp_date(x, _):
    try:
        dt = mdates.num2date(x)
        return f"{dt.year}年{dt.month}月{dt.day}日"
    except Exception:
        return ""


def api_get(path: str, params: dict = None, suppress_404: bool = False):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        if suppress_404 and r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"API エラー: {detail}")
        return None


def _safe_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def truncate(text, limit: int) -> str:
    s = _safe_str(text)
    return s if len(s) <= limit else s[:limit] + "..."


def is_truncated(full: str, limit: int) -> bool:
    return len(full) > limit


def api_post(path: str, body: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"登録失敗: {detail}")
        return None
    except Exception as e:
        st.error(f"API エラー: {e}")
        return None


def api_put(path: str, body: dict):
    try:
        r = requests.put(f"{API_BASE}{path}", json=body, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"更新失敗: {detail}")
        return None
    except Exception as e:
        st.error(f"API エラー: {e}")
        return None


def api_delete(path: str):
    try:
        r = requests.delete(f"{API_BASE}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        st.error(f"削除失敗: {detail}")
        return None
    except Exception as e:
        st.error(f"API エラー: {e}")
        return None


def _plot_metric(df: pd.DataFrame, col: str, title: str, yunit: str, selected_users: list):
    plt.clf()
    fig, ax = plt.subplots(figsize=(10, 3.5))
    has_data = False
    for uid in selected_users:
        udf = (
            df[df["user_id"] == uid]
            .dropna(subset=[col])
            .sort_values("date")
        )
        print(f"DEBUG: {title} [{USER_LABELS[uid]}] {len(udf)} points (unique dates)", flush=True)
        print("udf dates:", udf["date"].nunique(), flush=True)                               # ④
        print("x values:", list(udf["date"]), flush=True)                                    # ⑤
        if not udf.empty:
            ax.plot(
                udf["date"], udf[col],
                marker="o", label=USER_LABELS[uid],
                color=USER_COLORS[uid], linewidth=2, markersize=5,
            )
            has_data = True
    if has_data:
        ax.set_title(title, fontsize=13)
        ax.set_xlabel("日付", fontsize=10)
        ax.set_ylabel(yunit, fontsize=10)
        if col in ("weight", "temperature", "body_fat", "muscle_mass"):
            ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.1f}"))
        all_dates = sorted(df["date"].unique())
        ax.set_xticks(all_dates)
        print("xticks:", ax.get_xticks(), flush=True)                                        # ⑥
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        fig.autofmt_xdate(rotation=30)
        fig.canvas.draw()
        print("xticklabels:", [t.get_text() for t in ax.get_xticklabels()], flush=True)     # ⑦
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig, clear_figure=True)
        print("DEBUG: Labels fixed with DateFormatter('%m-%d')", flush=True)
    else:
        st.info(f"{title}のデータがありません")
    plt.close(fig)


# ── サイドバー ──────────────────────────────────────────
with st.sidebar:
    st.header("フィルター")
    selected_users: list = st.multiselect(
        "ユーザー",
        options=USER_IDS,
        default=["self"],
        format_func=lambda x: USER_LABELS[x],
    )

    today = date.today()
    date_start = st.date_input("開始日", value=today - timedelta(days=30))
    date_end = st.date_input("終了日", value=datetime.now(JST).date())

    st.divider()
    if st.button("更新"):
        fetch_latest.clear()
        fetch_range_data.clear()
        st.rerun()

    st.caption("※ データは非同期で反映されます。表示が更新されない場合は「更新」を押してください。")

    if st.button("ヘルスチェック"):
        r = api_get("/api/health/health")
        if r:
            st.success(f"OK — {r.get('db','')}")


# ── サマリーカード ──────────────────────────────────────
st.subheader("直近データ — 家族全員")
card_cols = st.columns(3)
for i, uid in enumerate(USER_IDS):
    with card_cols[i]:
        st.markdown(f"### {USER_LABELS[uid]}")
        latest = fetch_latest(uid)
        if latest:
            st.metric("体重",       f"{latest['weight']:.1f} kg"         if latest.get("weight")        is not None else "—")
            st.metric("体温",       f"{latest['temperature']:.1f} ℃"    if latest.get("temperature")  is not None else "—")
            st.metric("脈拍",       f"{latest['pulse']} bpm"         if latest.get("pulse")         is not None else "—")
            st.metric("収縮期血圧", f"{latest['systolic_bp']} mmHg" if latest.get("systolic_bp") is not None else "—")
            st.metric("拡張期血圧", f"{latest['diastolic_bp']} mmHg" if latest.get("diastolic_bp") is not None else "—")
            st.caption(f"最終更新: {latest['date']}")
        else:
            st.info("データなし")

st.divider()


# ── タブ ────────────────────────────────────────────────
tab_graph, tab_list, tab_create, tab_edit = st.tabs(
    ["グラフ", "一覧", "新規登録", "修正・削除"]
)


# ────────────────────────────────
# タブ 1: グラフ
# ────────────────────────────────
with tab_graph:
    st.subheader("時系列グラフ（複数ユーザー比較）")

    if not selected_users:
        st.info("サイドバーでユーザーを1人以上選択してください。")
    else:
        data = fetch_range_data(str(date_start), str(date_end))

        if not data:
            st.info("データがありません")
        else:
            df = pd.DataFrame(data)
            print("raw:", len(df), flush=True)                                                # ①
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            print("unique dates:", df["date"].nunique(), flush=True)                          # ②
            df = df[df["user_id"].isin(selected_users)]

            df = (
                df.sort_values("date")
                  .groupby(["user_id", "date"], as_index=False)
                  .last()
            )
            print("after_groupby:", len(df), flush=True)
            print("max dup:", df.groupby(["user_id","date"]).size().max(), flush=True)        # ③

            if df.empty:
                st.info("選択した期間・ユーザーのデータがありません")
            else:
                _plot_metric(df, "weight",       "体重", "kg",  selected_users)
                _plot_metric(df, "temperature", "体温", "℃",  selected_users)
                _plot_metric(df, "pulse",        "脈拍", "bpm", selected_users)

                # 血圧グラフ（参考線付き）
                plt.clf()
                fig_bp, ax_bp = plt.subplots(figsize=(10, 4))
                has_bp = False
                for uid in selected_users:
                    udf = (
                        df[df["user_id"] == uid]
                        .dropna(subset=["systolic_bp", "diastolic_bp"])
                        .sort_values("date")
                    )
                    print(f"DEBUG: 血圧 [{USER_LABELS[uid]}] {len(udf)} points (unique dates)", flush=True)
                    if not udf.empty:
                        ax_bp.plot(
                            udf["date"], udf["systolic_bp"],
                            marker="o", label=f"{USER_LABELS[uid]} 収縮期",
                            color=USER_COLORS[uid], linestyle="-", linewidth=2, markersize=5,
                        )
                        ax_bp.plot(
                            udf["date"], udf["diastolic_bp"],
                            marker="s", label=f"{USER_LABELS[uid]} 拡張期",
                            color=USER_COLORS[uid], linestyle="--", linewidth=2, markersize=5,
                        )
                        has_bp = True
                if has_bp:
                    ax_bp.axhline(y=120, color="gray",      linestyle="--", alpha=0.7, linewidth=1, label="目標: 収縮期 120")
                    ax_bp.axhline(y=80,  color="lightgray", linestyle="--", alpha=0.7, linewidth=1, label="目標: 拡張期 80")
                    ax_bp.set_title("血圧 (mmHg)", fontsize=13)
                    ax_bp.set_xlabel("日付", fontsize=10)
                    ax_bp.set_ylabel("mmHg", fontsize=10)
                    all_dates = sorted(df["date"].unique())
                    ax_bp.set_xticks(all_dates)
                    ax_bp.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
                    fig_bp.autofmt_xdate(rotation=30)
                    ax_bp.legend(loc="upper left", fontsize=9, ncol=2)
                    ax_bp.grid(True, alpha=0.3)
                    plt.tight_layout()
                    st.pyplot(fig_bp, clear_figure=True)
                else:
                    st.info("血圧データがありません")
                plt.close(fig_bp)


# ────────────────────────────────
# タブ 2: 一覧
# ────────────────────────────────
with tab_list:
    st.subheader("データ一覧")

    page = st.number_input("ページ", min_value=1, value=1, step=1)
    page_size = 20
    offset = (page - 1) * page_size

    params = {"limit": page_size, "offset": offset}
    if len(selected_users) == 1:
        params["user_id"] = selected_users[0]

    records = api_get("/api/health/records", params=params)
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


# ────────────────────────────────
# タブ 3: 新規登録
# ────────────────────────────────
with tab_create:
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
            form_temp = st.number_input(
                "体温 (°C)", min_value=34.0, max_value=42.0,
                value=None, step=0.1, format="%.1f",
            )
            form_pulse = st.number_input(
                "脈拍 (bpm)", min_value=30, max_value=200,
                value=None, step=1,
            )
        with c2:
            form_sys = st.number_input(
                "収縮期血圧 (mmHg)", min_value=50, max_value=250,
                value=None, step=1,
            )
            form_dia = st.number_input(
                "拡張期血圧 (mmHg)", min_value=30, max_value=150,
                value=None, step=1,
            )
            form_weight = st.number_input(
                "体重 (kg)", min_value=0.1, max_value=299.9,
                value=None, step=0.1, format="%.1f",
            )
            form_bf = st.number_input(
                "体脂肪率 (%)", min_value=0.0, max_value=100.0,
                value=None, step=0.1, format="%.1f",
            )
        form_muscle = st.number_input(
            "筋肉量 (kg)", min_value=0.1, max_value=199.9,
            value=None, step=0.1, format="%.1f",
        )
        form_bmr = st.number_input(
            "基礎代謝 (kcal)", min_value=1, max_value=4999,
            value=None, step=1,
        )
        form_memo = st.text_input("メモ", value="")
        form_meal_detail  = st.text_area("食事ログ", value="")
        form_activity_log = st.text_area("行動ログ", value="")

        submitted = st.form_submit_button("登録")

    if submitted:
        body = {
            "request_id": str(uuid.uuid4()),
            "user_id": form_user,
            "date": str(form_date),
            "memo": form_memo or "",
        }
        if form_temp is not None:
            body["temperature"] = float(form_temp)
        if form_pulse is not None:
            body["pulse"] = int(form_pulse)
        if form_sys is not None:
            body["systolic_bp"] = int(form_sys)
        if form_dia is not None:
            body["diastolic_bp"] = int(form_dia)
        if form_weight is not None:
            body["weight"] = float(form_weight)
        if form_bf is not None:
            body["body_fat"] = float(form_bf)
        if form_muscle is not None:
            body["muscle_mass"] = float(form_muscle)
        if form_bmr is not None:
            body["bmr"] = int(form_bmr)
        body["meal_detail"]  = form_meal_detail  or ""
        body["activity_log"] = form_activity_log or ""

        result = api_post("/api/health/record", body)
        if result:
            st.success("登録を受け付けました（反映には数秒かかる場合があります）")
            fetch_latest.clear()
            fetch_range_data.clear()
            st.rerun()


# ────────────────────────────────
# タブ 4: 修正・削除
# ────────────────────────────────
with tab_edit:
    st.subheader("修正・削除")

    # ── ユーザー選択 ──
    edit_user = st.selectbox(
        "編集するユーザー",
        options=USER_IDS,
        format_func=lambda x: USER_LABELS[x],
        key="edit_user_select",
    )

    # ── 登録済み日付一覧を取得 ──
    edit_records_list = api_get(
        "/api/health/records",
        params={"user_id": edit_user, "limit": 500},
    ) or []
    edit_dates = sorted({r["date"] for r in edit_records_list}, reverse=True)

    if not edit_dates:
        st.info(f"{USER_LABELS[edit_user]}の登録済みデータがありません")
    else:
        edit_date = st.selectbox(
            "編集する日付",
            options=edit_dates,
            key="edit_date_select",
        )

        # ── 選択した日付のレコードを取得 ──
        current_for_edit = api_get(
            "/api/health/record/day",
            params={"user_id": edit_user, "date": edit_date},
            suppress_404=True,
        )

        if not current_for_edit:
            st.warning(f"{edit_date} のレコードが見つかりません")
        else:
            rec = current_for_edit

            def _fval(key, cast=float):
                v = rec.get(key)
                return cast(v) if v is not None else None

            with st.form(f"edit_form_{edit_user}_{edit_date}"):
                e1, e2 = st.columns(2)
                with e1:
                    edit_temp  = st.number_input("体温 (°C)",        min_value=34.0, max_value=42.0,  value=_fval("temperature"),        step=0.1, format="%.1f")
                    edit_pulse = st.number_input("脈拍 (bpm)",        min_value=30,   max_value=200,   value=_fval("pulse", int),         step=1)
                    edit_sys   = st.number_input("収縮期血圧 (mmHg)", min_value=50,   max_value=250,   value=_fval("systolic_bp", int),   step=1)
                    edit_dia   = st.number_input("拡張期血圧 (mmHg)", min_value=30,   max_value=150,   value=_fval("diastolic_bp", int),  step=1)
                with e2:
                    edit_weight = st.number_input("体重 (kg)",        min_value=0.1,  max_value=299.9, value=_fval("weight"),             step=0.1, format="%.1f")
                    edit_bf     = st.number_input("体脂肪率 (%)",      min_value=0.0,  max_value=100.0, value=_fval("body_fat"),           step=0.1, format="%.1f")
                    edit_muscle = st.number_input("筋肉量 (kg)",       min_value=0.1,  max_value=199.9, value=_fval("muscle_mass"),        step=0.1, format="%.1f")
                    edit_bmr    = st.number_input("基礎代謝 (kcal)",   min_value=1,    max_value=4999,  value=_fval("bmr", int),           step=1)
                edit_memo = st.text_input("メモ", value=rec.get("memo") or "")
                edit_meal_detail = st.text_area(
                    "食事ログ",
                    value=rec.get("meal_detail") or ""
                )
                edit_activity_log = st.text_area(
                    "行動ログ",
                    value=rec.get("activity_log") or ""
                )
                update_btn = st.form_submit_button("更新")

            if update_btn:
                body = {}
                if edit_temp   is not None: body["temperature"] = float(edit_temp)
                if edit_pulse  is not None: body["pulse"]        = int(edit_pulse)
                if edit_sys    is not None: body["systolic_bp"]  = int(edit_sys)
                if edit_dia    is not None: body["diastolic_bp"] = int(edit_dia)
                if edit_weight is not None: body["weight"]       = float(edit_weight)
                if edit_bf     is not None: body["body_fat"]     = float(edit_bf)
                if edit_muscle is not None: body["muscle_mass"]  = float(edit_muscle)
                if edit_bmr    is not None: body["bmr"]          = int(edit_bmr)
                body["memo"] = edit_memo or ""
                body["meal_detail"] = edit_meal_detail or ""
                body["activity_log"] = edit_activity_log or ""

                result = api_put(f"/api/health/record/{rec['id']}", body)
                if result:
                    st.success(f"更新完了 — {edit_date} ({USER_LABELS[edit_user]})")
                    fetch_latest.clear()
                    fetch_range_data.clear()
                    st.rerun()

    st.divider()
    st.markdown("**削除**")

    if st.session_state.get("clear_del_id"):
        if "del_id" in st.session_state:
            st.session_state["del_id"] = None
        del st.session_state["clear_del_id"]

    delete_id = st.number_input("削除するレコード ID", min_value=1, step=1, value=None, key="del_id")

    if delete_id is not None:
        del_preview = api_get(f"/api/health/record/{int(delete_id)}", suppress_404=True)
    else:
        del_preview = None

    if del_preview:
        st.markdown("**削除対象レコード:**")
        disp = {k: v for k, v in del_preview.items() if k != "request_id"}
        disp["ユーザー"] = USER_LABELS.get(disp.pop("user_id", ""), "")
        if "created_at" in disp and disp["created_at"]:
            disp["created_at"] = to_jst(disp["created_at"])
        st.table(pd.DataFrame([disp]))

        confirm_delete = st.checkbox(f"上記レコード（ID: {delete_id}）を削除することを確認します")
        if st.button("削除実行", disabled=not confirm_delete):
            result = api_delete(f"/api/health/record/{int(delete_id)}")
            if result:
                st.success(f"削除完了 — ID: {result.get('id')}")
                st.session_state["clear_del_id"] = True
                fetch_latest.clear()
                fetch_range_data.clear()
                st.rerun()
    else:
        if delete_id is not None:
            st.warning(f"ID {int(delete_id)} のレコードは存在しません")
