from pathlib import Path
import importlib
import ast
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest


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


def test_manual_filter_period_survives_midnight():
    from filter_state import initialize_date_filters

    state = {}
    initialize_date_filters(state, date(2026, 9, 28))
    state["filter_date_start"] = date(2026, 9, 1)
    state["filter_date_end"] = date(2026, 9, 20)
    state["filter_start_manual"] = True
    state["filter_end_manual"] = True

    initialize_date_filters(state, date(2026, 9, 29))

    assert state["filter_date_start"] == date(2026, 9, 1)
    assert state["filter_date_end"] == date(2026, 9, 20)


def test_untouched_filter_period_tracks_jst_midnight():
    from filter_state import initialize_date_filters

    state = {}
    initialize_date_filters(state, date(2026, 9, 28))
    initialize_date_filters(state, date(2026, 9, 29))

    assert state["filter_date_start"] == date(2026, 8, 30)
    assert state["filter_date_end"] == date(2026, 9, 29)


@pytest.mark.parametrize("manual", [False, True])
def test_periodic_sidebar_fragment_requests_full_rerun_at_midnight(manual):
    from filter_state import initialize_date_filters

    source = _read("biolog_streamlit/streamlit_app.py")
    module = ast.parse(source)
    function = next(
        node for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "render_refresh_caption"
    )
    assert ast.unparse(function.decorator_list[0]) == "st.fragment(run_every='10s')"
    sidebar = next(
        node for node in module.body
        if isinstance(node, ast.With) and ast.unparse(node.items[0].context_expr) == "st.sidebar"
    )
    assert any(
        isinstance(node, ast.Expr) and ast.unparse(node.value) == "render_refresh_caption()"
        for node in sidebar.body
    )

    state = {}
    initialize_date_filters(state, date(2026, 9, 30))
    if manual:
        state.update({
            "filter_date_start": date(2026, 9, 10),
            "filter_date_end": date(2026, 9, 20),
            "filter_start_manual": True,
            "filter_end_manual": True,
        })

    class FullRerun(Exception):
        pass

    fake_st = SimpleNamespace(
        session_state=state,
        fragment=lambda **kwargs: lambda fn: fn,
        rerun=lambda: (_ for _ in ()).throw(FullRerun()),
        caption=lambda text: None,
    )
    clock = SimpleNamespace(now=lambda tz: SimpleNamespace(date=lambda: date(2026, 10, 1)))
    namespace = {"st": fake_st, "datetime": clock, "JST": object()}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "streamlit_app.py", "exec"), namespace)

    with pytest.raises(FullRerun):
        namespace["render_refresh_caption"]()

    # The requested full rerun reinitializes sidebar widgets and view arguments.
    initialize_date_filters(state, date(2026, 10, 1))
    assert state["filter_date_start"] == (date(2026, 9, 10) if manual else date(2026, 9, 1))
    assert state["filter_date_end"] == (date(2026, 9, 20) if manual else date(2026, 10, 1))
    namespace["render_refresh_caption"]()


def test_graph_and_summary_refresh_like_list():
    for path in ("graph.py", "list_view.py", "summary.py"):
        source = _read(f"biolog_streamlit/views/{path}")
        assert '@st.fragment(run_every="10s")' in source


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


def test_st_html_is_limited_to_the_style_module():
    matches = []
    for path in (PROJECT_ROOT / "biolog_streamlit").rglob("*.py"):
        if "st.html(" in path.read_text(encoding="utf-8"):
            matches.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert matches == ["biolog_streamlit/ui_style.py"]


def test_number_input_styles_are_injected_from_the_app_entrypoint():
    app_source = _read("biolog_streamlit/streamlit_app.py")
    style_source = _read("biolog_streamlit/ui_style.py")

    assert "from ui_style import inject_number_input_styles" in app_source
    assert "inject_number_input_styles()" in app_source
    # The stylesheet must stay a constant: no interpolation into st.html().
    assert "st.html(_NUMBER_INPUT_STYLE)" in style_source
    assert 'data-testid="InputInstructions"' in style_source


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
