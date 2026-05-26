from datetime import datetime, timezone
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def to_jst(dt) -> str:
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace(" ", "T"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")
