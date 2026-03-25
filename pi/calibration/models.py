"""Structured data models for AS7341 calibration artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class CalibrationMetrics:
    rmse: float
    mae: float
    median_abs_error: float
    r2: float
    residual_min: float
    residual_max: float
    residual_mean: float


@dataclass(frozen=True)
class CalibrationProfile:
    profile_id: str
    created_at: str
    calibration_version: str
    node_id: str
    fixture_id: str
    fixture_model: str
    sensor_board_id: str
    operator: str
    sensor_settings: dict[str, int]
    mount_assumptions: dict[str, object]
    regression_type: str
    feature_names: list[str]
    intercept: float
    coefficients: list[float]
    training_sample_count: int
    validation_sample_count: int
    metrics: CalibrationMetrics
    calibration_status: str
    notes: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["metrics"] = asdict(self.metrics)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "CalibrationProfile":
        return cls(
            profile_id=data["profile_id"],
            created_at=data["created_at"],
            calibration_version=data["calibration_version"],
            node_id=data.get("node_id", ""),
            fixture_id=data.get("fixture_id", ""),
            fixture_model=data.get("fixture_model", ""),
            sensor_board_id=data.get("sensor_board_id", ""),
            operator=data.get("operator", ""),
            sensor_settings=dict(data.get("sensor_settings", {})),
            mount_assumptions=dict(data.get("mount_assumptions", {})),
            regression_type=data["regression_type"],
            feature_names=list(data["feature_names"]),
            intercept=float(data["intercept"]),
            coefficients=[float(v) for v in data["coefficients"]],
            training_sample_count=int(data["training_sample_count"]),
            validation_sample_count=int(data["validation_sample_count"]),
            metrics=CalibrationMetrics(**data["metrics"]),
            calibration_status=data.get("calibration_status", "draft"),
            notes=data.get("notes", ""),
        )


@dataclass(frozen=True)
class ValidationReport:
    generated_at: str
    profile_id: str
    regression_type: str
    training_sample_count: int
    validation_sample_count: int
    metrics: CalibrationMetrics
    feature_names: list[str]
    notes: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["metrics"] = asdict(self.metrics)
        return data
