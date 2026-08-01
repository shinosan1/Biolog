import os

API_BASE = os.getenv("BIOLOG_API_URL", "http://localhost:8766")

# phase 7aでコンテナTZをAsia/Tokyoへ変更した前後の保存形式境界。
# このID以前のcreated_atはUTC、以後はJSTのnaive文字列として保存されている。
LEGACY_UTC_MAX_RECORD_ID = 146

USER_LABELS = {"self": "自分", "father": "父", "mother": "母"}
USER_IDS = list(USER_LABELS.keys())
USER_COLORS = {"self": "#1f77b4", "father": "#2ca02c", "mother": "#d62728"}
