"""Validation helpers for AS7341 calibration sessions."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pi.calibration.fit_model import compute_metrics
from pi.calibration.models import ValidationReport
from pi.calibration.profile_io import load_profile


def split_records(records: list[dict[str, object]], holdout_stride: int = 4) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    explicit_validate = [record for record in records if str(record.get("split", "")).lower() == "validate"]
    explicit_train = [record for record in records if str(record.get("split", "")).lower() == "train"]
    if explicit_validate:
        train = explicit_train or [record for record in records if str(record.get("split", "")).lower() != "validate"]
        return train, explicit_validate

    if len(records) < 6:
        return records, records

    train = []
    validate = []
    for idx, record in enumerate(records):
        if (idx + 1) % holdout_stride == 0:
            validate.append(record)
        else:
            train.append(record)
    return train, validate or train


def build_validation_report(profile_path: Path, validation_records: list[dict[str, object]]) -> ValidationReport:
    profile = load_profile(profile_path)
    metrics = compute_metrics(
        validation_records,
        profile.feature_names,
        profile.intercept,
        profile.coefficients,
    )
    return ValidationReport(
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        profile_id=profile.profile_id,
        regression_type=profile.regression_type,
        training_sample_count=profile.training_sample_count,
        validation_sample_count=len(validation_records),
        metrics=metrics,
        feature_names=profile.feature_names,
        notes=profile.notes,
    )


def validation_report_markdown(report: ValidationReport) -> str:
    metrics = report.metrics
    return (
        f"# AS7341 Validation Report\n\n"
        f"- Generated: {report.generated_at}\n"
        f"- Profile ID: {report.profile_id}\n"
        f"- Regression: {report.regression_type}\n"
        f"- Training samples: {report.training_sample_count}\n"
        f"- Validation samples: {report.validation_sample_count}\n"
        f"- Features: {', '.join(report.feature_names)}\n\n"
        f"## Metrics\n\n"
        f"- RMSE: {metrics.rmse} umol/m2/s\n"
        f"- MAE: {metrics.mae} umol/m2/s\n"
        f"- Median absolute error: {metrics.median_abs_error} umol/m2/s\n"
        f"- R2: {metrics.r2}\n"
        f"- Residual min/max: {metrics.residual_min} / {metrics.residual_max} umol/m2/s\n"
        f"- Residual mean: {metrics.residual_mean} umol/m2/s\n"
    )
