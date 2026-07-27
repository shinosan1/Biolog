import sys
from pathlib import Path


STREAMLIT_DIR = Path(__file__).resolve().parents[1] / "biolog_streamlit"
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

from form_fields import MEASUREMENT_FIELDS
from form_state import merge_measurement_values


NAMES = tuple(field.name for field in MEASUREMENT_FIELDS)


class _FakeStreamlit:
    def __init__(self, session_state=None):
        self.session_state = dict(session_state or {})
        self.calls = []
        self.key_present_at_call = []

    def number_input(self, **kwargs):
        self.calls.append(kwargs)
        self.key_present_at_call.append(kwargs["key"] in self.session_state)
        if kwargs["key"] in self.session_state:
            return self.session_state[kwargs["key"]]
        value = kwargs.get("value", kwargs["min_value"])
        self.session_state[kwargs["key"]] = value
        return value

    def text_input(self, label, value="", key=None, **kwargs):
        self.calls.append({"label": label, "value": value, "key": key, **kwargs})
        return self.session_state.get(key, value)


def _values(**overrides):
    values = {name: None for name in NAMES}
    values.update(overrides)
    return values


def test_initial_state_uses_all_api_measurements():
    api = _values(weight=64.2, body_fat=18.0)

    merged = merge_measurement_values(NAMES, api, None, {})

    assert merged.values == api
    assert merged.baseline == api
    assert merged.conflicts == ()


def test_number_input_uses_default_only_before_session_key_exists(monkeypatch):
    import form_components

    field = MEASUREMENT_FIELDS[0]
    fake = _FakeStreamlit()
    monkeypatch.setattr(form_components, "st", fake)

    form_components._number_input(field, 64.0, "create_weight")

    assert fake.calls[0]["value"] == 64.0


def test_number_input_uses_session_state_without_default_on_rerender(monkeypatch):
    import form_components

    field = MEASUREMENT_FIELDS[0]
    fake = _FakeStreamlit({"create_weight": 63.5})
    monkeypatch.setattr(form_components, "st", fake)

    result = form_components._number_input(field, None, "create_weight")

    assert "value" not in fake.calls[0]
    assert result == 63.5


def test_number_input_preserves_none_on_rerender(monkeypatch):
    import form_components

    field = MEASUREMENT_FIELDS[0]
    fake = _FakeStreamlit({"create_weight": None})
    monkeypatch.setattr(form_components, "st", fake)

    result = form_components._number_input(field, None, "create_weight")

    assert fake.calls[0]["value"] is None
    assert fake.key_present_at_call == [True]
    assert result is None
    assert fake.session_state["create_weight"] is None


def test_empty_measurements_do_not_fall_back_to_minimums_on_rerender(monkeypatch):
    import form_components

    fake = _FakeStreamlit({f"create_{field.name}": None for field in MEASUREMENT_FIELDS})
    monkeypatch.setattr(form_components, "st", fake)

    results = {
        field.name: form_components._number_input(field, None, f"create_{field.name}")
        for field in MEASUREMENT_FIELDS
    }

    assert results == _values()
    assert all(call["value"] is None for call in fake.calls)


def test_edit_measurement_with_none_api_value_stays_empty(monkeypatch):
    import form_components

    field = MEASUREMENT_FIELDS[0]
    key = "edit_self_2026-07-23_weight"
    fake = _FakeStreamlit({key: None})
    monkeypatch.setattr(form_components, "st", fake)

    result = form_components._number_input(field, None, key)

    assert result is None
    assert fake.calls[0]["value"] is None


def test_create_measurements_use_isolated_text_input_keys(monkeypatch):
    import form_components

    old_minimums = {
        f"create_{field.name}": field.min_value
        for field in MEASUREMENT_FIELDS
    }
    text_values = {
        f"create_{field.name}_text": str(field.min_value + field.step)
        for field in MEASUREMENT_FIELDS
    }
    fake = _FakeStreamlit({**old_minimums, **text_values})
    monkeypatch.setattr(form_components, "st", fake)

    results = {
        field.name: form_components._create_measurement_input(
            field, f"create_{field.name}"
        )
        for field in MEASUREMENT_FIELDS
    }

    assert results == {
        field.name: str(field.min_value + field.step)
        for field in MEASUREMENT_FIELDS
    }
    assert [call["key"] for call in fake.calls] == [
        f"create_{field.name}_text"
        for field in MEASUREMENT_FIELDS
    ]


def test_external_change_updates_an_unedited_field():
    previous = _values(body_fat=None)
    api = _values(body_fat=18.0)

    merged = merge_measurement_values(NAMES, api, previous, previous)

    assert merged.values["body_fat"] == 18.0
    assert merged.conflicts == ()


def test_user_edit_is_preserved_when_api_is_unchanged():
    previous = _values(weight=64.2)
    widget = _values(weight=63.5)

    merged = merge_measurement_values(NAMES, previous, previous, widget)

    assert merged.values["weight"] == 63.5
    assert merged.conflicts == ()


def test_different_user_and_api_changes_are_merged():
    previous = _values(weight=64.2, body_fat=None)
    widget = _values(weight=63.5, body_fat=None)
    api = _values(weight=64.2, body_fat=18.0)

    merged = merge_measurement_values(NAMES, api, previous, widget)

    assert merged.values["weight"] == 63.5
    assert merged.values["body_fat"] == 18.0
    assert merged.conflicts == ()


def test_same_field_conflict_preserves_user_value():
    previous = _values(body_fat=17.0)
    widget = _values(body_fat=17.5)
    api = _values(body_fat=18.0)

    merged = merge_measurement_values(NAMES, api, previous, widget)

    assert merged.values["body_fat"] == 17.5
    assert merged.baseline["body_fat"] == 17.0
    assert merged.conflicts == ("body_fat",)


def test_api_value_matching_user_edit_resolves_without_conflict():
    previous = _values(body_fat=17.0)
    widget = _values(body_fat=18.0)
    api = _values(body_fat=18.0)

    merged = merge_measurement_values(NAMES, api, previous, widget)

    assert merged.values["body_fat"] == 18.0
    assert merged.baseline["body_fat"] == 18.0
    assert merged.conflicts == ()


def test_none_integer_float_and_zero_are_not_conflated():
    previous = _values(pulse=None, body_fat=0.0)
    widget = _values(pulse=0, body_fat=0.0)
    api = _values(pulse=None, body_fat=0)

    merged = merge_measurement_values(NAMES, api, previous, widget)

    assert merged.values["pulse"] == 0
    assert merged.values["body_fat"] == 0
    assert type(merged.values["body_fat"]) is int
    assert merged.conflicts == ()


def test_session_adapter_writes_api_value_before_widget_render():
    import form_components

    session_state = {
        "edit_self_2026-07-19_body_fat": None,
        "edit_self_2026-07-19__api_measurements": _values(body_fat=None),
    }
    record = _values(body_fat=18.0)

    conflicts = form_components.sync_edit_measurement_state(
        session_state,
        "edit_self_2026-07-19",
        record,
    )

    assert conflicts == ()
    assert session_state["edit_self_2026-07-19_body_fat"] == 18.0


def test_different_record_prefix_initializes_independent_widget_state():
    import form_components

    session_state = {
        "edit_self_2026-07-18_body_fat": 17.0,
        "edit_self_2026-07-18__api_measurements": _values(body_fat=17.0),
    }

    conflicts = form_components.sync_edit_measurement_state(
        session_state,
        "edit_self_2026-07-19",
        _values(body_fat=18.0),
    )

    assert conflicts == ()
    assert session_state["edit_self_2026-07-18_body_fat"] == 17.0
    assert session_state["edit_self_2026-07-19_body_fat"] == 18.0


def test_accept_latest_replaces_only_conflicted_fields():
    import form_components

    prefix = "edit_self_2026-07-19"
    session_state = {
        f"{prefix}_weight": 63.5,
        f"{prefix}_body_fat": 17.5,
        f"{prefix}__api_measurements": _values(weight=64.2, body_fat=17.0),
    }
    record = _values(weight=64.2, body_fat=18.0)

    form_components.accept_latest_measurements(
        session_state,
        prefix,
        record,
        ("body_fat",),
    )

    assert session_state[f"{prefix}_weight"] == 63.5
    assert session_state[f"{prefix}_body_fat"] == 18.0
