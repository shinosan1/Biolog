import pandas as pd
import streamlit as st


_TABLE_STYLE = """
<style>
.biolog-table-wrap {
    max-width: 100%;
    overflow-x: auto;
}
.biolog-table {
    border-collapse: collapse;
    min-width: 100%;
    width: max-content;
    font-size: 0.875rem;
}
.biolog-table th,
.biolog-table td {
    border-bottom: 1px solid rgba(128, 128, 128, 0.35);
    padding: 0.45rem 0.6rem;
    text-align: left;
    vertical-align: top;
    white-space: pre-wrap;
}
.biolog-table th {
    font-weight: 600;
    white-space: nowrap;
}
</style>
"""


def dataframe_to_safe_html(df: pd.DataFrame) -> str:
    display_df = df.astype(object).where(pd.notna(df), "")
    table_html = display_df.to_html(
        index=False,
        escape=True,
        border=0,
        na_rep="",
        classes=["biolog-table"],
    )
    # table_html is the only non-constant HTML inserted here. Keep escape=True
    # above and never interpolate raw user values into this wrapper.
    return f'{_TABLE_STYLE}<div class="biolog-table-wrap">{table_html}</div>'


def render_safe_table(df: pd.DataFrame) -> None:
    st.markdown(dataframe_to_safe_html(df), unsafe_allow_html=True)
