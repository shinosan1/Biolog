from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class NumberField:
    name: str
    label: str
    min_value: int | float
    max_value: int | float
    step: int | float
    cast: Callable
    fmt: str | None = None
    create_group: str = ""
    edit_group: str = ""


# Keep this order identical to the create/edit form display order.
MEASUREMENT_FIELDS = [
    NumberField("weight", "体重 (kg)", 0.1, 299.9, 0.1, float, "%.1f", "left", "left"),
    NumberField("temperature", "体温 (°C)", 34.0, 42.0, 0.1, float, "%.1f", "left", "left"),
    NumberField("systolic_bp", "収縮期血圧 (mmHg)", 50, 250, 1, int, None, "left", "left"),
    NumberField("diastolic_bp", "拡張期血圧 (mmHg)", 30, 150, 1, int, None, "left", "left"),
    NumberField("pulse", "脈拍 (bpm)", 30, 200, 1, int, None, "right", "right"),
    NumberField("body_fat", "体脂肪率 (%)", 0.0, 100.0, 0.1, float, "%.1f", "right", "right"),
    NumberField("bmr", "基礎代謝 (kcal)", 1, 4999, 1, int, None, "right", "right"),
    NumberField("muscle_mass", "筋肉量 (kg)", 0.1, 199.9, 0.1, float, "%.1f", "right", "right"),
]
