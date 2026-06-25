import pandas as pd


def _safe_str(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v)


def truncate(text, limit: int) -> str:
    s = _safe_str(text)
    return s if len(s) <= limit else s[:limit] + "..."


def is_truncated(full: str, limit: int) -> bool:
    return len(full) > limit
