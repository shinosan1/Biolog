from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

USER_IDS = {"self", "father", "mother"}


# API 層バリデーション責務:
#   入力値の型・範囲チェック（UX 目的、422 でユーザーに即時フィードバック）
#   DB CHECK 制約とは独立して管理する。
#   ビジネスロジック依存のルールはここに書く。
#
# DB CHECK 制約の役割:
#   最終防衛ライン（絶対条件のみ）。
#   数値レンジ、NOT NULL、UNIQUE のみ。
#   複雑条件・状態依存ルールは書かない。
class HealthRecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str          # デフォルト削除（preprocess 担当）
    date: str                # Optional + default_date validator 削除（preprocess 担当）
    user_id: str
    temperature: Optional[float] = None
    pulse: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    muscle_mass:  Optional[float] = None
    bmr:          Optional[int]   = None
    meal_detail:  Optional[str]   = None
    activity_log: Optional[str]   = None
    memo:         str = ""

    @field_validator("user_id")
    @classmethod
    def valid_user_id(cls, v):
        if v not in USER_IDS:
            raise ValueError(f"user_id must be one of {sorted(USER_IDS)}")
        return v

    @field_validator("temperature")
    @classmethod
    def valid_temperature(cls, v):
        if v is not None and not (34.0 <= v <= 42.0):
            raise ValueError("temperature must be between 34.0 and 42.0 °C")
        return v

    @field_validator("pulse")
    @classmethod
    def valid_pulse(cls, v):
        if v is not None and not (30 <= v <= 200):
            raise ValueError("pulse must be between 30 and 200 bpm")
        return v

    @field_validator("systolic_bp")
    @classmethod
    def valid_systolic_bp(cls, v):
        if v is not None and not (50 <= v <= 250):
            raise ValueError("systolic_bp must be between 50 and 250 mmHg")
        return v

    @field_validator("diastolic_bp")
    @classmethod
    def valid_diastolic_bp(cls, v):
        if v is not None and not (30 <= v <= 150):
            raise ValueError("diastolic_bp must be between 30 and 150 mmHg")
        return v

    @field_validator("weight")
    @classmethod
    def valid_weight(cls, v):
        if v is not None and not (0 < v < 300):
            raise ValueError("weight must be between 0 and 300 kg")
        return v

    @field_validator("body_fat")
    @classmethod
    def valid_body_fat(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("body_fat must be between 0 and 100 %")
        return v

    @field_validator("muscle_mass")
    @classmethod
    def valid_muscle_mass(cls, v):
        if v is not None and not (0 < v < 200):
            raise ValueError("muscle_mass must be between 0 and 200 kg")
        return v

    @field_validator("bmr")
    @classmethod
    def valid_bmr(cls, v):
        if v is not None and not (0 < v < 5000):
            raise ValueError("bmr must be between 0 and 5000 kcal")
        return v

    @model_validator(mode="after")
    def at_least_one_measurement(self):
        fields = [
            self.temperature, self.pulse, self.systolic_bp, self.diastolic_bp,
            self.weight, self.body_fat, self.muscle_mass, self.bmr,
        ]
        if all(f is None for f in fields):
            raise ValueError("At least one measurement field must be provided")
        return self


# API 層バリデーション責務（HealthRecordCreate と同じ方針）
class HealthRecordUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temperature: Optional[float] = None
    pulse: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    weight: Optional[float] = None
    body_fat: Optional[float] = None
    muscle_mass: Optional[float] = None
    bmr: Optional[int] = None
    memo:         Optional[str] = None
    meal_detail:  Optional[str] = None
    activity_log: Optional[str] = None

    @field_validator("temperature")
    @classmethod
    def valid_temperature(cls, v):
        if v is not None and not (34.0 <= v <= 42.0):
            raise ValueError("temperature must be between 34.0 and 42.0 °C")
        return v

    @field_validator("pulse")
    @classmethod
    def valid_pulse(cls, v):
        if v is not None and not (30 <= v <= 200):
            raise ValueError("pulse must be between 30 and 200 bpm")
        return v

    @field_validator("systolic_bp")
    @classmethod
    def valid_systolic_bp(cls, v):
        if v is not None and not (50 <= v <= 250):
            raise ValueError("systolic_bp must be between 50 and 250 mmHg")
        return v

    @field_validator("diastolic_bp")
    @classmethod
    def valid_diastolic_bp(cls, v):
        if v is not None and not (30 <= v <= 150):
            raise ValueError("diastolic_bp must be between 30 and 150 mmHg")
        return v

    @field_validator("weight")
    @classmethod
    def valid_weight(cls, v):
        if v is not None and not (0 < v < 300):
            raise ValueError("weight must be between 0 and 300 kg")
        return v

    @field_validator("body_fat")
    @classmethod
    def valid_body_fat(cls, v):
        if v is not None and not (0.0 <= v <= 100.0):
            raise ValueError("body_fat must be between 0 and 100 %")
        return v

    @field_validator("muscle_mass")
    @classmethod
    def valid_muscle_mass(cls, v):
        if v is not None and not (0 < v < 200):
            raise ValueError("muscle_mass must be between 0 and 200 kg")
        return v

    @field_validator("bmr")
    @classmethod
    def valid_bmr(cls, v):
        if v is not None and not (0 < v < 5000):
            raise ValueError("bmr must be between 0 and 5000 kcal")
        return v
