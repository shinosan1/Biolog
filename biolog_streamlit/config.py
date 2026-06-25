import os

API_BASE = os.getenv("BIOLOG_API_URL", "http://localhost:8766")

USER_LABELS = {"self": "自分", "father": "父", "mother": "母"}
USER_IDS = list(USER_LABELS.keys())
USER_COLORS = {"self": "#1f77b4", "father": "#2ca02c", "mother": "#d62728"}
