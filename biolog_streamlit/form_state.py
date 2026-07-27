from dataclasses import dataclass
from typing import Iterable, Mapping


_MISSING = object()


@dataclass(frozen=True)
class MeasurementMerge:
    values: dict
    baseline: dict
    conflicts: tuple[str, ...]


def _same_value(left, right) -> bool:
    return type(left) is type(right) and left == right


def merge_measurement_values(
    field_names: Iterable[str],
    api_values: Mapping[str, object],
    previous_api_values: Mapping[str, object] | None,
    widget_values: Mapping[str, object],
) -> MeasurementMerge:
    """Three-way merge API values into edit widget state."""
    names = tuple(field_names)
    if previous_api_values is None:
        values = {name: api_values.get(name) for name in names}
        return MeasurementMerge(values, dict(values), ())

    values = {}
    baseline = {}
    conflicts = []
    for name in names:
        current_api = api_values.get(name)
        previous_api = previous_api_values.get(name)
        widget_value = widget_values.get(name, _MISSING)

        if widget_value is _MISSING:
            values[name] = current_api
            baseline[name] = current_api
        elif _same_value(current_api, previous_api):
            values[name] = widget_value
            baseline[name] = previous_api
        elif _same_value(widget_value, previous_api) or _same_value(widget_value, current_api):
            values[name] = current_api
            baseline[name] = current_api
        else:
            values[name] = widget_value
            baseline[name] = previous_api
            conflicts.append(name)

    return MeasurementMerge(values, baseline, tuple(conflicts))
