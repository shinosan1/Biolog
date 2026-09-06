from datetime import timedelta


def initialize_date_filters(session_state, today) -> None:
    """Advance untouched defaults at JST midnight, preserving manual dates."""
    previous_today = session_state.get("filter_defaults_today")
    if previous_today != today:
        if not session_state.get("filter_start_manual"):
            session_state["filter_date_start"] = today - timedelta(days=30)
        if not session_state.get("filter_end_manual"):
            session_state["filter_date_end"] = today
        session_state["filter_defaults_today"] = today
    session_state.setdefault("filter_date_start", today - timedelta(days=30))
    session_state.setdefault("filter_date_end", today)
