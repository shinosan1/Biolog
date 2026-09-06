import streamlit as st

from form_fields import MEASUREMENT_FIELDS
from form_state import merge_field_values


EDIT_TEXT_FIELDS = ("memo", "meal_detail", "activity_log")


def _initial_value(record: dict | None, field):
    if not record:
        return None
    value = record.get(field.name)
    return field.cast(value) if value is not None else None


def _number_input(field, value, key: str):
    kwargs = {
        "label": field.label,
        "min_value": field.min_value,
        "max_value": field.max_value,
        "step": field.step,
        "key": key,
    }
    if key not in st.session_state:
        kwargs["value"] = value
    elif st.session_state[key] is None:
        # Keep the existing empty widget state. Deleting the key here can make
        # Streamlit recreate the widget with min_value in a real browser.
        kwargs["value"] = None
    if field.fmt:
        kwargs["format"] = field.fmt
    return st.number_input(**kwargs)


def create_measurement_state_keys(key_prefix: str) -> tuple[str, ...]:
    """Session state keys held by the create-mode measurement inputs."""
    return tuple(
        f"{key_prefix}_{field.name}_text"
        for field in MEASUREMENT_FIELDS
    )


def _create_measurement_input(field, key: str):
    """Render an optional create measurement without number_input min fallback."""
    return st.text_input(
        field.label,
        value="",
        key=f"{key}_text",
    )


def _measurement_values(record: dict | None) -> dict:
    return {
        field.name: _initial_value(record, field)
        for field in MEASUREMENT_FIELDS
    }


def _sync_edit_state(session_state, key_prefix: str, api_values: dict, baseline_key: str) -> tuple[str, ...]:
    """Synchronize API values before edit widgets are instantiated."""
    names = tuple(api_values)
    widget_values = {
        name: session_state[f"{key_prefix}_{name}"]
        for name in names
        if f"{key_prefix}_{name}" in session_state
    }
    merged = merge_field_values(
        names,
        api_values,
        session_state.get(baseline_key),
        widget_values,
    )
    for name, value in merged.values.items():
        session_state[f"{key_prefix}_{name}"] = value
    session_state[baseline_key] = merged.baseline
    return merged.conflicts


def sync_edit_measurement_state(session_state, key_prefix: str, record: dict) -> tuple[str, ...]:
    return _sync_edit_state(
        session_state, key_prefix, _measurement_values(record),
        f"{key_prefix}__api_measurements",
    )


def _text_values(record: dict) -> dict:
    return {name: record.get(name) or "" for name in EDIT_TEXT_FIELDS}


def sync_edit_text_state(session_state, key_prefix: str, record: dict) -> tuple[str, ...]:
    return _sync_edit_state(
        session_state, key_prefix, _text_values(record),
        f"{key_prefix}__api_text",
    )


def _accept_latest_values(session_state, key_prefix: str, api_values: dict, baseline_key: str, field_names: tuple[str, ...]) -> None:
    baseline = dict(session_state.get(baseline_key) or {})
    for name in field_names:
        value = api_values[name]
        session_state[f"{key_prefix}_{name}"] = value
        baseline[name] = value
    session_state[baseline_key] = baseline


def accept_latest_measurements(
    session_state,
    key_prefix: str,
    record: dict,
    field_names: tuple[str, ...],
) -> None:
    _accept_latest_values(
        session_state, key_prefix, _measurement_values(record),
        f"{key_prefix}__api_measurements", field_names,
    )


def accept_latest_text(session_state, key_prefix: str, record: dict, field_names: tuple[str, ...]) -> None:
    _accept_latest_values(
        session_state, key_prefix, _text_values(record),
        f"{key_prefix}__api_text", field_names,
    )


def render_measurement_inputs(
    mode: str,
    key_prefix: str,
    record: dict | None = None,
    left_col=None,
    right_col=None,
) -> dict:
    values = {}
    if left_col is None or right_col is None:
        left, right = st.columns(2)
    else:
        left, right = left_col, right_col

    def render_group(group: str):
        for field in MEASUREMENT_FIELDS:
            field_group = field.create_group if mode == "create" else field.edit_group
            if field_group != group:
                continue
            key = f"{key_prefix}_{field.name}"
            if mode == "create":
                values[field.name] = _create_measurement_input(field, key)
            else:
                values[field.name] = _number_input(
                    field,
                    _initial_value(record, field),
                    key,
                )

    with left:
        render_group("left")
    with right:
        render_group("right")
    render_group("below")
    return values
