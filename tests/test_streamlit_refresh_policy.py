from pathlib import Path
import importlib

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_list_view_keeps_periodic_fragment_without_arrow_table():
    source = _read("biolog_streamlit/views/list_view.py")

    assert '@st.fragment(run_every="10s")' in source
    assert "def render_list(" in source
    assert "st.dataframe" not in source


def test_sidebar_explains_automatic_refresh():
    source = _read("biolog_streamlit/streamlit_app.py")

    assert 'st.button("更新")' in source
    assert "clear_health_caches()" in source
    assert "約10秒ごとに自動更新" in source


def test_no_streamlit_arrow_table_widgets_remain_in_application():
    for path in (PROJECT_ROOT / "biolog_streamlit").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "st.dataframe" not in source, path
        assert "st.table" not in source, path


def test_both_record_tables_use_safe_renderer():
    for relative_path in (
        "biolog_streamlit/views/list_view.py",
        "biolog_streamlit/views/edit.py",
    ):
        assert "render_safe_table(" in _read(relative_path)


def test_unsafe_html_is_limited_to_safe_table_renderer():
    matches = []
    for path in (PROJECT_ROOT / "biolog_streamlit").rglob("*.py"):
        if "unsafe_allow_html=True" in path.read_text(encoding="utf-8"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert matches == ["biolog_streamlit/safe_table.py"]


def test_safe_table_escapes_values_columns_and_preserves_text():
    dataframe_to_safe_html = importlib.import_module(
        "safe_table"
    ).dataframe_to_safe_html
    frame = pd.DataFrame({
        "<script>column</script>": [
            '<script>alert(1)</script><img src=x onerror="alert(2)">'
        ],
        "日本語": ["</div><script>alert(3)</script> & 改行\n維持"],
    })

    html = dataframe_to_safe_html(frame)

    assert "<script>column</script>" not in html
    assert "<script>alert" not in html
    assert "<img src=x" not in html
    assert "&lt;script&gt;column&lt;/script&gt;" in html
    assert '&lt;img src=x onerror="alert(2)"&gt;' in html
    assert "&lt;/div&gt;&lt;script&gt;alert(3)&lt;/script&gt; &amp; 改行\\n維持" in html


def test_safe_table_renders_missing_cells_as_blank():
    dataframe_to_safe_html = importlib.import_module(
        "safe_table"
    ).dataframe_to_safe_html
    frame = pd.DataFrame({
        "NaN": [float("nan")],
        "None": [None],
        "pd.NA": [pd.NA],
    })

    html = dataframe_to_safe_html(frame)

    assert "<td>NaN</td>" not in html
    assert "<td>None</td>" not in html
    assert "<td>&lt;NA&gt;</td>" not in html
    assert html.count("<td></td>") == 3
