"""Tests for AS7341 calibration helpers."""

from pathlib import Path

from pi.calibration.fit_model import build_profile
from pi.calibration.profile_io import load_profile, save_profile
from pi.calibration.runtime_estimator import AS7341RuntimeEstimator
from pi.calibration.validate_model import build_validation_report, split_records


def _record(idx: int, split: str = "train") -> dict[str, object]:
    base = 100 + idx * 9
    return {
        "timestamp": f"2026-03-24T21:{idx:02d}:00+00:00",
        "node_id": "growlab-v0",
        "fixture_id": "fixture-a",
        "fixture_model": "LM301H strip",
        "calibration_profile_id": "",
        "operator": "tester",
        "sensor_board_id": "board-01",
        "gain": 7.0,
        "integration_time": 29.0,
        "astep": 599.0,
        "led_pwm_percent": float(20 + idx * 10),
        "fixture_distance_cm": 30.0,
        "lateral_offset_cm": 0.0,
        "reference_ppfd": float(35 + idx * 17 + (idx % 3) * 4),
        "split": split,
        "notes": "",
        "as7341_415nm": float(base + idx * 2),
        "as7341_445nm": float(base * 1.3 + idx),
        "as7341_480nm": float(base * 1.7 + idx * idx),
        "as7341_515nm": float(base * 2.1 + idx * 3),
        "as7341_555nm": float(base * 2.6 + idx * 4),
        "as7341_590nm": float(base * 2.2 + idx * 5),
        "as7341_630nm": float(base * 1.4 + idx * 6),
        "as7341_680nm": float(base * 0.9 + idx * 7),
        "as7341_clear": float(base * 3.0 + idx * 8),
        "as7341_nir": float(base * 0.5 + idx * 2),
    }


class TestCalibrationProfileIO:
    def test_save_and_load_profile(self, tmp_path: Path):
        training = [_record(i) for i in range(12)]
        validation = [_record(12, split="validate"), _record(13, split="validate")]
        profile = build_profile(
            profile_id="profile-1",
            training_records=training,
            validation_records=validation,
            regression_type="ridge",
        )

        path = tmp_path / "profile.json"
        save_profile(path, profile)
        loaded = load_profile(path)

        assert loaded.profile_id == "profile-1"
        assert loaded.feature_names == profile.feature_names
        assert loaded.metrics.rmse >= 0


class TestSplitRecords:
    def test_prefers_explicit_validate_rows(self):
        rows = [_record(0, split="train"), _record(1, split="validate")]
        train, validate = split_records(rows)
        assert len(train) == 1
        assert len(validate) == 1
        assert validate[0]["split"] == "validate"


class TestRuntimeEstimator:
    def test_estimates_ppfd_when_settings_match(self):
        training = [_record(i) for i in range(12)]
        validation = [_record(12, split="validate"), _record(13, split="validate")]
        profile = build_profile(
            profile_id="profile-1",
            training_records=training,
            validation_records=validation,
            regression_type="ridge",
        )
        estimator = AS7341RuntimeEstimator(profile)

        channels = {key: int(float(training[0][key])) for key in training[0] if key.startswith("as7341_")}
        estimate, status = estimator.estimate(
            channels,
            gain=7,
            integration_time=29,
            astep=599,
            node_id="growlab-v0",
        )

        assert status == "calibrated"
        assert estimate is not None
        assert estimate >= 0

    def test_refuses_mismatched_settings(self):
        training = [_record(i) for i in range(12)]
        profile = build_profile(
            profile_id="profile-1",
            training_records=training,
            validation_records=training,
            regression_type="ridge",
        )
        estimator = AS7341RuntimeEstimator(profile)
        channels = {key: int(float(training[0][key])) for key in training[0] if key.startswith("as7341_")}

        estimate, status = estimator.estimate(
            channels,
            gain=6,
            integration_time=29,
            astep=599,
            node_id="growlab-v0",
        )

        assert estimate is None
        assert status == "settings_mismatch"


class TestValidationReport:
    def test_build_validation_report(self, tmp_path: Path):
        training = [_record(i) for i in range(12)]
        validation = [_record(12, split="validate"), _record(13, split="validate")]
        profile = build_profile(
            profile_id="profile-1",
            training_records=training,
            validation_records=validation,
            regression_type="ridge",
        )
        profile_path = tmp_path / "profile.json"
        save_profile(profile_path, profile)

        report = build_validation_report(profile_path, validation)
        assert report.profile_id == "profile-1"
        assert report.validation_sample_count == 2
        assert report.metrics.rmse >= 0
