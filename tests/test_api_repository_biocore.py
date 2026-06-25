def _payload(**overrides):
    base = {
        "request_id": "rid-1",
        "date": "2026-06-25",
        "user_id": "self",
        "temperature": 36.5,
        "pulse": 72,
        "systolic_bp": 120,
        "diastolic_bp": 80,
        "weight": 61.2,
        "body_fat": 20.1,
        "muscle_mass": 42.3,
        "bmr": 1400,
        "meal_detail": "meal",
        "activity_log": "act",
        "memo": "memo",
    }
    base.update(overrides)
    return base


EXPECTED_RECORD_KEYS = [
    "id",
    "request_id",
    "date",
    "user_id",
    "temperature",
    "pulse",
    "systolic_bp",
    "diastolic_bp",
    "weight",
    "body_fat",
    "muscle_mass",
    "bmr",
    "meal_detail",
    "activity_log",
    "memo",
    "created_at",
]


def test_insert_upsert_idempotent_and_reads(temp_db_modules):
    write_repository, biocore, _db_path = temp_db_modules

    assert write_repository.insert_record(_payload()) == {"id": 1}

    row = biocore.get_record_by_id(1)
    assert list(row.keys()) == EXPECTED_RECORD_KEYS
    assert row["request_id"] == "rid-1"
    assert row["weight"] == 61.2

    result = write_repository.insert_record(_payload(request_id="rid-2", weight=62.0))
    assert set(result) == {"id"}

    by_day = biocore.get_record_by_user_date("self", "2026-06-25")
    assert by_day["request_id"] == "rid-2"
    assert by_day["weight"] == 62.0

    assert write_repository.insert_record(
        _payload(request_id="rid-2", date="2026-06-26")
    ) == {"idempotent": True, "id": 1}

    assert list(biocore.get_latest_record("self").keys()) == EXPECTED_RECORD_KEYS
    assert list(biocore.get_health_records(user_id="self", limit=20, offset=0)[0].keys()) == EXPECTED_RECORD_KEYS
    assert list(biocore.get_health_records_by_date_range("2026-06-01", "2026-06-30")[0].keys()) == EXPECTED_RECORD_KEYS


def test_update_keeps_existing_values_for_none_and_reports_empty_or_missing(temp_db_modules):
    write_repository, biocore, _db_path = temp_db_modules
    write_repository.insert_record(_payload())

    assert write_repository.update_record({
        "id": 1,
        "weight": 63.4,
        "temperature": None,
        "memo": "",
    }) == {"id": 1, "updated": 1}

    row = biocore.get_record_by_id(1)
    assert row["weight"] == 63.4
    assert row["temperature"] == 36.5
    assert row["memo"] == ""

    try:
        write_repository.update_record({"id": 1, "unknown": "x", "temperature": None})
    except ValueError as e:
        assert str(e) == "No fields to update"
    else:
        raise AssertionError("empty update did not fail")

    try:
        write_repository.update_record({"id": 999, "memo": "x"})
    except ValueError as e:
        assert str(e) == "Record 999 not found"
    else:
        raise AssertionError("missing update did not fail")


def test_delete_existing_and_missing_record(temp_db_modules):
    write_repository, biocore, _db_path = temp_db_modules
    write_repository.insert_record(_payload())

    assert write_repository.delete_record({"id": 1}) == {"id": 1, "deleted": 1}
    assert biocore.get_record_by_id(1) is None

    try:
        write_repository.delete_record({"id": 1})
    except ValueError as e:
        assert str(e) == "Record 1 not found"
    else:
        raise AssertionError("missing delete did not fail")
