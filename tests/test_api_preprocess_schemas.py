import pytest


def test_preprocess_record_fills_stable_values_and_splits_blood_pressure(monkeypatch):
    import preprocess

    monkeypatch.setattr(preprocess.uuid, "uuid4", lambda: "fixed-request-id")
    monkeypatch.setattr(preprocess, "jst_date", lambda: "2026-06-25")

    result = preprocess.preprocess_record({
        "user_id": "self",
        "pulse": 72.9,
        "bmr": "1400.0",
        "blood_pressure": "120－80mmHg",
    })

    assert result["request_id"] == "fixed-request-id"
    assert result["date"] == "2026-06-25"
    assert result["pulse"] == 72
    assert result["bmr"] == 1400
    assert result["systolic_bp"] == 120
    assert result["diastolic_bp"] == 80
    assert "blood_pressure" not in result


def test_preprocess_record_keeps_existing_bp_fields_over_split_values(monkeypatch):
    import preprocess

    monkeypatch.setattr(preprocess.uuid, "uuid4", lambda: "fixed-request-id")
    monkeypatch.setattr(preprocess, "jst_date", lambda: "2026-06-25")

    result = preprocess.preprocess_record({
        "request_id": "existing",
        "date": "2026-06-24",
        "systolic_bp": 111,
        "blood_pressure": "120/80",
    })

    assert result["request_id"] == "existing"
    assert result["date"] == "2026-06-24"
    assert result["systolic_bp"] == 111
    assert result["diastolic_bp"] == 80


def test_health_record_create_validation_accepts_valid_record():
    from schemas import HealthRecordCreate

    record = HealthRecordCreate(
        request_id="rid",
        date="2026-06-25",
        user_id="self",
        weight=61.2,
    )

    assert record.user_id == "self"
    assert record.weight == 61.2


@pytest.mark.parametrize(
    "field,value",
    [
        ("activity_log", "AI生態資源動画編集"),
        ("meal_detail", "白ご飯、サラダチキン"),
        ("memo", "テストデータ入力"),
        ("body_fat", 0.0),
    ],
)
def test_health_record_create_accepts_each_health_value(field, value):
    from schemas import HealthRecordCreate

    record = HealthRecordCreate(**{
        "request_id": "rid",
        "date": "2026-07-19",
        "user_id": "self",
        field: value,
    })

    assert getattr(record, field) == value


def test_health_record_create_accepts_null_memo_with_activity_log():
    from schemas import HealthRecordCreate

    record = HealthRecordCreate(
        request_id="rid",
        date="2026-07-19",
        user_id="self",
        activity_log="AI生態資源動画編集",
        memo=None,
    )

    assert record.activity_log == "AI生態資源動画編集"
    assert record.memo is None


@pytest.mark.parametrize(
    "payload",
    [
        {"request_id": "rid", "date": "2026-06-25", "user_id": "other", "weight": 61.2},
        {"request_id": "rid", "date": "2026-06-25", "user_id": "self"},
        {"request_id": "rid", "date": "2026-06-25", "user_id": "self", "activity_log": ""},
        {"request_id": "rid", "date": "2026-06-25", "user_id": "self", "meal_detail": "  ", "memo": None},
        {"request_id": "rid", "date": "2026-06-25", "user_id": "self", "temperature": 50.0},
        {"request_id": "rid", "date": "2026-06-25", "user_id": "self", "weight": 61.2, "extra": "x"},
    ],
)
def test_health_record_create_rejects_invalid_payloads(payload):
    from pydantic import ValidationError
    from schemas import HealthRecordCreate

    with pytest.raises(ValidationError):
        HealthRecordCreate(**payload)


def test_health_record_update_validation_and_extra_forbid():
    from pydantic import ValidationError
    from schemas import HealthRecordUpdate

    assert HealthRecordUpdate(weight=61.2).weight == 61.2

    with pytest.raises(ValidationError):
        HealthRecordUpdate(weight=400)

    with pytest.raises(ValidationError):
        HealthRecordUpdate(weight=61.2, extra="x")
