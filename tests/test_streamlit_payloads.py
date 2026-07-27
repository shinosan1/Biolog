from datetime import date

import pytest


def test_build_create_payload_preserves_types_and_empty_strings(monkeypatch):
    import payloads

    monkeypatch.setattr(payloads.uuid, "uuid4", lambda: "fixed-request-id")
    body = payloads.build_create_payload(
        user_id="self",
        form_date=date(2026, 6, 25),
        measurements={
            "temperature": 36.5,
            "pulse": 0,
            "systolic_bp": None,
            "diastolic_bp": 80,
            "weight": None,
            "body_fat": 0.0,
            "muscle_mass": None,
            "bmr": 1400,
        },
        memo="",
        meal_detail="",
        activity_log="act",
    )

    assert body == {
        "request_id": "fixed-request-id",
        "user_id": "self",
        "date": "2026-06-25",
        "memo": "",
        "temperature": 36.5,
        "pulse": 0,
        "diastolic_bp": 80,
        "body_fat": 0.0,
        "bmr": 1400,
        "meal_detail": "",
        "activity_log": "act",
    }


def test_build_update_payload_skips_none_but_keeps_zero():
    from payloads import build_update_payload

    body = build_update_payload(
        measurements={
            "temperature": None,
            "pulse": 0,
            "systolic_bp": None,
            "diastolic_bp": 80,
            "weight": None,
            "body_fat": 0.0,
            "muscle_mass": None,
            "bmr": None,
        },
        memo="",
        meal_detail="meal",
        activity_log="",
    )

    assert body == {
        "pulse": 0,
        "diastolic_bp": 80,
        "body_fat": 0.0,
        "memo": "",
        "meal_detail": "meal",
        "activity_log": "",
    }


def test_create_payload_converts_weight_text_to_float(monkeypatch):
    import payloads

    monkeypatch.setattr(payloads.uuid, "uuid4", lambda: "fixed-request-id")
    body = payloads.build_create_payload(
        user_id="self",
        form_date=date(2026, 7, 23),
        measurements={"weight": "64.2"},
        memo="",
        meal_detail="",
        activity_log="",
    )

    assert body["weight"] == 64.2


def test_create_payload_skips_blank_weight_text():
    from payloads import build_create_payload

    body = build_create_payload(
        user_id="self",
        form_date=date(2026, 7, 23),
        measurements={"weight": "  "},
        memo="",
        meal_detail="",
        activity_log="",
    )

    assert "weight" not in body


@pytest.mark.parametrize("weight", ["abc", "0", "300"])
def test_create_payload_rejects_invalid_weight_text(weight):
    from payloads import build_create_payload

    with pytest.raises(ValueError):
        build_create_payload(
            user_id="self",
            form_date=date(2026, 7, 23),
            measurements={"weight": weight},
            memo="",
            meal_detail="",
            activity_log="",
        )


def test_create_payload_converts_all_measurement_text_values():
    from payloads import build_create_payload

    body = build_create_payload(
        user_id="self",
        form_date=date(2026, 7, 23),
        measurements={
            "weight": "64.2",
            "temperature": "36.5",
            "systolic_bp": "120",
            "diastolic_bp": "80",
            "pulse": "72",
            "body_fat": "18.0",
            "bmr": "1400",
            "muscle_mass": "45.0",
        },
        memo="",
        meal_detail="",
        activity_log="",
    )

    assert {field: body[field] for field in (
        "weight", "temperature", "systolic_bp", "diastolic_bp",
        "pulse", "body_fat", "bmr", "muscle_mass",
    )} == {
        "weight": 64.2,
        "temperature": 36.5,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "pulse": 72,
        "body_fat": 18.0,
        "bmr": 1400,
        "muscle_mass": 45.0,
    }


def test_form_fields_order_and_layout_groups_match_existing_forms():
    from form_fields import MEASUREMENT_FIELDS

    assert [field.name for field in MEASUREMENT_FIELDS] == [
        "weight",
        "temperature",
        "systolic_bp",
        "diastolic_bp",
        "pulse",
        "body_fat",
        "bmr",
        "muscle_mass",
    ]
    assert [field.create_group for field in MEASUREMENT_FIELDS] == [
        "left",
        "left",
        "left",
        "left",
        "right",
        "right",
        "right",
        "right",
    ]
    assert [field.edit_group for field in MEASUREMENT_FIELDS] == [
        "left",
        "left",
        "left",
        "left",
        "right",
        "right",
        "right",
        "right",
    ]


def test_formatters_safe_str_and_truncate():
    import math

    from formatters import _safe_str, is_truncated, truncate

    assert _safe_str(None) == ""
    assert _safe_str(math.nan) == ""
    assert truncate("abcdef", 3) == "abc..."
    assert truncate("abc", 3) == "abc"
    assert is_truncated("abcd", 3) is True
    assert is_truncated("abc", 3) is False
