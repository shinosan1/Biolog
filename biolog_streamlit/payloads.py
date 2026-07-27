import uuid

from form_fields import MEASUREMENT_FIELDS


def _add_measurements(body: dict, values: dict):
    for field in MEASUREMENT_FIELDS:
        value = values.get(field.name)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        validate_range = isinstance(value, str)
        try:
            converted = field.cast(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field.label}は数値で入力してください") from exc
        if validate_range and (converted < field.min_value or converted > field.max_value):
            raise ValueError(
                f"{field.label}は{field.min_value}〜{field.max_value}の範囲で入力してください"
            )
        body[field.name] = converted


def build_create_payload(
    *,
    user_id: str,
    form_date,
    measurements: dict,
    memo: str,
    meal_detail: str,
    activity_log: str,
) -> dict:
    body = {
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "date": str(form_date),
        "memo": memo or "",
    }
    _add_measurements(body, measurements)
    body["meal_detail"] = meal_detail or ""
    body["activity_log"] = activity_log or ""
    return body


def build_update_payload(
    *,
    measurements: dict,
    memo: str,
    meal_detail: str,
    activity_log: str,
) -> dict:
    body = {}
    _add_measurements(body, measurements)
    body["memo"] = memo or ""
    body["meal_detail"] = meal_detail or ""
    body["activity_log"] = activity_log or ""
    return body
