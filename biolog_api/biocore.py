from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from db_manager import get_connection


@contextmanager
def _read_conn():
    with get_connection(read=True) as conn:
        yield conn


def get_health_records(
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    if limit > 500:
        raise ValueError("limit too large (max 500)")
    if offset > 10000:
        raise ValueError("offset too large")

    if user_id:
        query = """
        SELECT id, request_id, date, user_id,
               temperature, pulse, systolic_bp, diastolic_bp,
               weight, body_fat, muscle_mass, bmr,
               meal_detail, activity_log,
               memo, created_at
        FROM health_records
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        LIMIT ? OFFSET ?
        """
        params = (user_id, limit, offset)
    else:
        query = """
        SELECT id, request_id, date, user_id,
               temperature, pulse, systolic_bp, diastolic_bp,
               weight, body_fat, muscle_mass, bmr,
               meal_detail, activity_log,
               memo, created_at
        FROM health_records
        ORDER BY date DESC, id DESC
        LIMIT ? OFFSET ?
        """
        params = (limit, offset)

    with _read_conn() as conn:
        cur = conn.execute(query, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_health_records_by_date_range(
    start_date: str,
    end_date: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if user_id:
        query = """
        SELECT id, request_id, date, user_id,
               temperature, pulse, systolic_bp, diastolic_bp,
               weight, body_fat, muscle_mass, bmr,
               meal_detail, activity_log,
               memo, created_at
        FROM health_records
        WHERE date >= ? AND date <= ? AND user_id = ?
        ORDER BY date ASC, id ASC
        """
        params = (start_date, end_date, user_id)
    else:
        query = """
        SELECT id, request_id, date, user_id,
               temperature, pulse, systolic_bp, diastolic_bp,
               weight, body_fat, muscle_mass, bmr,
               meal_detail, activity_log,
               memo, created_at
        FROM health_records
        WHERE date >= ? AND date <= ?
        ORDER BY date ASC, id ASC
        """
        params = (start_date, end_date)

    with _read_conn() as conn:
        cur = conn.execute(query, params)
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_record_by_id(record_id: int) -> Optional[Dict[str, Any]]:
    query = """
    SELECT id, request_id, date, user_id,
           temperature, pulse, systolic_bp, diastolic_bp,
           weight, body_fat, muscle_mass, bmr,
           meal_detail, activity_log,
           memo, created_at
    FROM health_records
    WHERE id = ?
    """
    with _read_conn() as conn:
        cur = conn.execute(query, (record_id,))
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None


def get_record_by_user_date(user_id: str, date: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT *
    FROM health_records
    WHERE user_id = ? AND date = ?
    """
    with _read_conn() as conn:
        cur = conn.execute(query, (user_id, date))
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None


def get_latest_record(user_id: str) -> Optional[Dict[str, Any]]:
    query = """
    SELECT id, request_id, date, user_id,
           temperature, pulse, systolic_bp, diastolic_bp,
           weight, body_fat, muscle_mass, bmr,
           meal_detail, activity_log,
           memo, created_at
    FROM health_records
    WHERE user_id = ?
    ORDER BY date DESC, id DESC
    LIMIT 1
    """
    with _read_conn() as conn:
        cur = conn.execute(query, (user_id,))
        cols = [c[0] for c in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None
