# biolog_api/preprocess.py
# 責務: schema normalization layer（構文正規化のみ）
#
# ── permitted transformations only ───────────────────────────────────
#   1. 型補正（type coercion）: float → int
#   2. 構造補完（structural normalization）: UUID/date の欠損補完
#   3. 構文クリーンアップ（syntactic cleanup）: BP 文字列分解
#
# これ以外（意味変換・カテゴリ化・単位変換・推論）は別層に追加すること
# ─────────────────────────────────────────────────────────────────────
import re
import uuid

from time_utils import jst_date


def preprocess_record(raw: dict) -> dict:
    """pure function: 外部サービス依存なし。"""
    data = dict(raw)

    # 1. 構造補完（欠損時のみ）
    if not data.get("request_id"):
        data["request_id"] = str(uuid.uuid4())
    if not data.get("date"):
        data["date"] = jst_date()

    # 2. 型補正（LLM が float で返す整数フィールドのみ。null は維持）
    for field in ("pulse", "bmr", "systolic_bp", "diastolic_bp"):
        v = data.get(field)
        if v is not None:
            try:
                data[field] = int(float(v))
            except (ValueError, TypeError):
                data[field] = None

    # 3. BP 文字列分解: "110/75", "110－75", "110/75mmHg" 等に対応
    bp = data.pop("blood_pressure", None)
    if bp and isinstance(bp, str):
        bp = re.sub(r'[－–—-]', '/', bp)           # ハイフン系を / に統一
        bp = re.sub(r'[^\d/\s]', '', bp).strip()   # 単位・記号を除去
        parts = re.split(r'[/ ]+', bp)
        if len(parts) == 2:
            try:
                data.setdefault("systolic_bp",  int(float(parts[0])))
                data.setdefault("diastolic_bp", int(float(parts[1])))
            except (ValueError, TypeError):
                pass

    # meal_detail / activity_log はそのまま通過（変換・結合禁止）
    return data
