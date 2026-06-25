import pandas as pd
import streamlit as st

from api_client import ApiClientError
from cache import fetch_range_data
from charts import plot_blood_pressure, plot_metric


def render_graph(selected_users: list, date_start, date_end):
    st.subheader("時系列グラフ（複数ユーザー比較）")

    if not selected_users:
        st.info("サイドバーでユーザーを1人以上選択してください。")
    else:
        try:
            data = fetch_range_data(str(date_start), str(date_end))
        except ApiClientError as e:
            st.error(f"API エラー: {e.message}")
            data = None

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
                plot_metric(df, "weight",       "体重", "kg",  selected_users)
                plot_metric(df, "temperature", "体温", "℃",  selected_users)
                plot_blood_pressure(df, selected_users)
                plot_metric(df, "pulse",        "脈拍", "bpm", selected_users)
