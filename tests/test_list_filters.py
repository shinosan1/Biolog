import importlib


def _records():
    return [
        {"id": 1, "user_id": "self", "date": "2026-07-01"},
        {"id": 2, "user_id": "father", "date": "2026-07-02"},
        {"id": 3, "user_id": "mother", "date": "2026-07-03"},
    ]


def test_two_selected_users_exclude_unselected_user():
    view = importlib.import_module("views.list_view")
    result = view._filter_records(_records(), ["self", "father"])

    assert set(result["user_id"]) == {"self", "father"}
    assert "mother" not in set(result["user_id"])


def test_single_selected_user_keeps_existing_filter_behavior():
    view = importlib.import_module("views.list_view")
    result = view._filter_records(_records(), ["self"])

    assert result["id"].tolist() == [1]


def test_no_selected_users_never_falls_back_to_all_records():
    view = importlib.import_module("views.list_view")
    result = view._filter_records(_records(), [])

    assert result.empty


def test_range_endpoint_is_used_for_list_and_csv():
    source = (
        importlib.import_module("pathlib").Path(__file__).resolve().parents[1]
        / "biolog_streamlit" / "views" / "list_view.py"
    ).read_text(encoding="utf-8")

    assert '"/api/health/records/range"' in source
    assert '"start": str(date_start)' in source
    assert '"end": str(date_end)' in source


def test_csv_formula_prefixes_are_neutralized():
    view = importlib.import_module("views.list_view")

    for value in ("=1+1", "+cmd", "-2+3", "@SUM(A1:A2)"):
        assert view._sanitize_csv_value(value) == "'" + value
    assert view._sanitize_csv_value("ordinary text") == "ordinary text"
    assert view._sanitize_csv_value(64.2) == 64.2
