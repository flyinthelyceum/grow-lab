"""Model fitting utilities for AS7341 commissioning sessions."""

from __future__ import annotations

import math
from datetime import timezone
from datetime import datetime

from pi.calibration.as7341_features import DEFAULT_FEATURE_NAMES, build_feature_vector
from pi.calibration.models import CalibrationMetrics, CalibrationProfile


def _transpose(matrix: list[list[float]]) -> list[list[float]]:
    return [list(row) for row in zip(*matrix)]


def _matmul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    out = [[0.0 for _ in range(len(b[0]))] for _ in range(len(a))]
    for i, row in enumerate(a):
        for k, value in enumerate(row):
            for j in range(len(b[0])):
                out[i][j] += value * b[k][j]
    return out


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[idx]] for idx, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda idx: abs(augmented[idx][col]))
        if abs(augmented[pivot][col]) < 1e-9:
            raise ValueError("Calibration fit is singular; collect more diverse samples")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]

        pivot_value = augmented[col][col]
        for j in range(col, size + 1):
            augmented[col][j] /= pivot_value

        for row in range(size):
            if row == col:
                continue
            factor = augmented[row][col]
            for j in range(col, size + 1):
                augmented[row][j] -= factor * augmented[col][j]

    return [augmented[idx][-1] for idx in range(size)]


def _fit_coefficients(
    records: list[dict[str, object]],
    feature_names: list[str],
    regression_type: str,
    ridge_alpha: float,
) -> tuple[float, list[float]]:
    x_rows = []
    y_values = []
    for record in records:
        x_rows.append([1.0] + build_feature_vector(record, feature_names))
        y_values.append(float(record["reference_ppfd"]))

    x_t = _transpose(x_rows)
    xtx = _matmul(x_t, x_rows)
    xty = [row[0] for row in _matmul(x_t, [[y] for y in y_values])]

    if regression_type == "ridge":
        for idx in range(1, len(xtx)):
            xtx[idx][idx] += ridge_alpha

    solution = _solve_linear_system(xtx, xty)
    return solution[0], solution[1:]


def predict_ppfd(record: dict[str, object], feature_names: list[str], intercept: float, coefficients: list[float]) -> float:
    prediction = intercept
    for name, coefficient in zip(feature_names, coefficients):
        prediction += coefficient * float(record[name])
    return prediction


def compute_metrics(
    records: list[dict[str, object]],
    feature_names: list[str],
    intercept: float,
    coefficients: list[float],
) -> CalibrationMetrics:
    actual = [float(record["reference_ppfd"]) for record in records]
    predicted = [
        predict_ppfd(record, feature_names, intercept, coefficients)
        for record in records
    ]
    residuals = [p - a for p, a in zip(predicted, actual)]
    abs_errors = sorted(abs(value) for value in residuals)

    mse = sum(value * value for value in residuals) / max(len(residuals), 1)
    mae = sum(abs_errors) / max(len(abs_errors), 1)
    median_abs_error = abs_errors[len(abs_errors) // 2] if abs_errors else 0.0
    mean_actual = sum(actual) / max(len(actual), 1)
    ss_total = sum((value - mean_actual) ** 2 for value in actual)
    ss_res = sum(value * value for value in residuals)
    r2 = 1.0 - (ss_res / ss_total) if ss_total > 0 else 0.0

    return CalibrationMetrics(
        rmse=round(math.sqrt(mse), 3),
        mae=round(mae, 3),
        median_abs_error=round(median_abs_error, 3),
        r2=round(r2, 4),
        residual_min=round(min(residuals) if residuals else 0.0, 3),
        residual_max=round(max(residuals) if residuals else 0.0, 3),
        residual_mean=round(sum(residuals) / max(len(residuals), 1), 3),
    )


def build_profile(
    *,
    profile_id: str,
    training_records: list[dict[str, object]],
    validation_records: list[dict[str, object]],
    feature_names: list[str] | None = None,
    regression_type: str = "linear",
    ridge_alpha: float = 1.0,
    calibration_status: str = "commissioned",
    notes: str = "",
) -> CalibrationProfile:
    feature_names = feature_names or list(DEFAULT_FEATURE_NAMES)
    intercept, coefficients = _fit_coefficients(
        training_records,
        feature_names,
        regression_type,
        ridge_alpha,
    )
    metrics = compute_metrics(
        validation_records or training_records,
        feature_names,
        intercept,
        coefficients,
    )

    exemplar = training_records[0]
    return CalibrationProfile(
        profile_id=profile_id,
        created_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        calibration_version="1",
        node_id=str(exemplar.get("node_id", "")),
        fixture_id=str(exemplar.get("fixture_id", "")),
        fixture_model=str(exemplar.get("fixture_model", "")),
        sensor_board_id=str(exemplar.get("sensor_board_id", "")),
        operator=str(exemplar.get("operator", "")),
        sensor_settings={
            "gain": int(float(exemplar.get("gain", 0))),
            "integration_time": int(float(exemplar.get("integration_time", 0))),
            "astep": int(float(exemplar.get("astep", 0))),
        },
        mount_assumptions={
            "orientation": "upward-facing",
            "geometry": "fixed per node",
            "diffuser_bound_to_calibration": True,
            "shroud_bound_to_calibration": True,
        },
        regression_type=regression_type,
        feature_names=feature_names,
        intercept=round(intercept, 6),
        coefficients=[round(value, 6) for value in coefficients],
        training_sample_count=len(training_records),
        validation_sample_count=len(validation_records),
        metrics=metrics,
        calibration_status=calibration_status,
        notes=notes,
    )
