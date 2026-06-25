import streamlit as st

from form_fields import MEASUREMENT_FIELDS


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
        "value": value,
        "step": field.step,
        "key": key,
    }
    if field.fmt:
        kwargs["format"] = field.fmt
    return st.number_input(**kwargs)


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
            values[field.name] = _number_input(
                field,
                _initial_value(record, field),
                f"{key_prefix}_{field.name}",
            )

    with left:
        render_group("left")
    with right:
        render_group("right")
    render_group("below")
    return values
