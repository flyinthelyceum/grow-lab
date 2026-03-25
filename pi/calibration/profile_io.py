"""Read and write calibration profiles."""

from __future__ import annotations

import json
from pathlib import Path

from pi.calibration.models import CalibrationProfile


def load_profile(path: Path) -> CalibrationProfile:
    return CalibrationProfile.from_dict(json.loads(path.read_text()))


def save_profile(path: Path, profile: CalibrationProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile.to_dict(), indent=2) + "\n")
