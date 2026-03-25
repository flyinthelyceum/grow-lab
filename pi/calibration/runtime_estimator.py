"""Runtime PPFD estimation from AS7341 channels and a calibration profile."""

from __future__ import annotations

import json
from pathlib import Path

from pi.calibration.fit_model import predict_ppfd
from pi.calibration.models import CalibrationProfile
from pi.calibration.profile_io import load_profile


class AS7341RuntimeEstimator:
    """Fixture-specific PPFD estimator for the installed AS7341 node."""

    def __init__(self, profile: CalibrationProfile) -> None:
        self.profile = profile

    @classmethod
    def from_path(cls, path: Path) -> "AS7341RuntimeEstimator":
        return cls(load_profile(path))

    def estimate(
        self,
        channels: dict[str, int],
        *,
        gain: int,
        integration_time: int,
        astep: int,
        node_id: str,
    ) -> tuple[float | None, str]:
        settings = self.profile.sensor_settings
        if (
            settings.get("gain") != gain
            or settings.get("integration_time") != integration_time
            or settings.get("astep") != astep
        ):
            return None, "settings_mismatch"

        if self.profile.node_id and node_id and self.profile.node_id != node_id:
            return None, "node_mismatch"

        prediction = predict_ppfd(
            channels,
            self.profile.feature_names,
            self.profile.intercept,
            self.profile.coefficients,
        )
        return max(round(prediction, 3), 0.0), "calibrated"

    def metadata_json(self, status: str) -> str:
        rmse = self.profile.metrics.rmse
        if rmse <= 20:
            confidence = "commissioned"
        elif rmse <= 35:
            confidence = "provisional"
        else:
            confidence = "low"
        return json.dumps(
            {
                "calibration_profile_id": self.profile.profile_id,
                "calibration_status": status,
                "confidence": confidence,
                "regression_type": self.profile.regression_type,
            }
        )
