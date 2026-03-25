"""CLI tools for AS7341 calibration and validation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import click

from pi.calibration.as7341_features import RAW_CHANNEL_FIELDS, extract_channel_map
from pi.calibration.capture_session import append_capture_row, ensure_session_file, read_capture_rows
from pi.calibration.fit_model import build_profile
from pi.calibration.profile_io import save_profile
from pi.calibration.validate_model import build_validation_report, split_records, validation_report_markdown
from pi.config.schema import AppConfig
from pi.discovery.registry import build_registry
from pi.discovery.scanner import scan_all


def _run_async(coro):
    return asyncio.run(coro)


def _coerce_record(row: dict[str, str]) -> dict[str, object]:
    numeric_fields = {
        "gain",
        "integration_time",
        "astep",
        "led_pwm_percent",
        "fixture_distance_cm",
        "lateral_offset_cm",
        "reference_ppfd",
        *RAW_CHANNEL_FIELDS,
    }
    record: dict[str, object] = {}
    for key, value in row.items():
        if key in numeric_fields and value != "":
            record[key] = float(value)
        else:
            record[key] = value
    return record


@click.group("calibration")
def calibration_group() -> None:
    """Calibration and validation workflows."""
    pass


@calibration_group.group("as7341")
def as7341_group() -> None:
    """AS7341 commissioning workflow."""
    pass


@as7341_group.command("init-session")
@click.option("--output", "output_path", required=True, type=click.Path())
def init_session(output_path: str) -> None:
    """Create an empty AS7341 calibration session CSV."""
    session_path = Path(output_path)
    ensure_session_file(session_path)
    click.echo(f"Created calibration session: {session_path}")


@as7341_group.command("capture")
@click.option("--session", "session_path", required=True, type=click.Path())
@click.option("--operator", default="", help="Operator name")
@click.option("--pwm-percent", required=True, type=float, help="Fixture dimmer percentage")
@click.option("--distance-cm", required=True, type=float, help="Fixture-to-canopy reference distance")
@click.option("--lateral-offset-cm", default=0.0, type=float, help="PAR meter lateral offset")
@click.option("--reference-ppfd", required=True, type=float, help="PPFD from rented PAR meter")
@click.option("--samples", default=5, type=int, help="Number of AS7341 reads to average")
@click.option("--settle-seconds", default=0.0, type=float, help="Optional settling delay before capture")
@click.option("--split", default="train", type=click.Choice(["train", "validate"]), help="Dataset split label")
@click.option("--notes", default="", help="Freeform capture notes")
@click.pass_context
def capture_row(
    ctx: click.Context,
    session_path: str,
    operator: str,
    pwm_percent: float,
    distance_cm: float,
    lateral_offset_cm: float,
    reference_ppfd: float,
    samples: int,
    settle_seconds: float,
    split: str,
    notes: str,
) -> None:
    """Capture one averaged AS7341 row into a session CSV."""
    config: AppConfig = ctx.obj["config"]

    async def _capture() -> None:
        if settle_seconds > 0:
            await asyncio.sleep(settle_seconds)

        result = scan_all(
            i2c_bus=config.i2c.bus,
            serial_port=config.serial.port,
        )
        registry = build_registry(config, result)
        driver = registry.get_driver("as7341")
        if driver is None:
            raise click.ClickException("AS7341 is not available. Run `growlab sensor scan` first.")

        accumulated = {name: 0.0 for name in RAW_CHANNEL_FIELDS}
        gain = integration_time = astep = 0

        for _ in range(samples):
            readings = await driver.read()
            channels = extract_channel_map(readings)
            gain = getattr(driver, "_gain", 0)
            integration_time = getattr(driver, "_atime", 0)
            astep = getattr(driver, "_astep", 0)
            for name in RAW_CHANNEL_FIELDS:
                accumulated[name] += channels[name]
            await asyncio.sleep(0.05)

        averaged = {
            name: round(accumulated[name] / max(samples, 1), 3)
            for name in RAW_CHANNEL_FIELDS
        }
        row = {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "node_id": config.installation.node_id,
            "fixture_id": config.installation.fixture_id,
            "fixture_model": config.installation.fixture_model,
            "calibration_profile_id": "",
            "operator": operator,
            "sensor_board_id": config.installation.sensor_board_id,
            "gain": gain,
            "integration_time": integration_time,
            "astep": astep,
            "led_pwm_percent": pwm_percent,
            "fixture_distance_cm": distance_cm,
            "lateral_offset_cm": lateral_offset_cm,
            "reference_ppfd": reference_ppfd,
            "split": split,
            "notes": notes,
        }
        row.update(averaged)
        append_capture_row(Path(session_path), row)

        click.echo(f"Captured {Path(session_path)}")
        click.echo(f"  reference_ppfd: {reference_ppfd:.1f} umol/m2/s")
        click.echo(f"  pwm_percent:    {pwm_percent:.1f}")
        click.echo(f"  distance_cm:    {distance_cm:.1f}")
        click.echo(f"  samples:        {samples}")

    _run_async(_capture())


@as7341_group.command("fit")
@click.option("--session", "session_path", required=True, type=click.Path(exists=True))
@click.option("--profile-out", required=True, type=click.Path())
@click.option("--profile-id", default="", help="Explicit profile id")
@click.option("--regression", type=click.Choice(["linear", "ridge"]), default="linear")
@click.option("--ridge-alpha", default=1.0, type=float)
@click.option("--holdout-stride", default=4, type=int, help="Deterministic validation stride when no split column is used")
@click.option("--notes", default="", help="Profile notes")
def fit_profile(
    session_path: str,
    profile_out: str,
    profile_id: str,
    regression: str,
    ridge_alpha: float,
    holdout_stride: int,
    notes: str,
) -> None:
    """Fit an AS7341 PPFD profile from a session CSV."""
    rows = [_coerce_record(row) for row in read_capture_rows(Path(session_path))]
    if len(rows) < 6:
        raise click.ClickException("Need at least 6 capture rows to fit a profile.")

    train_rows, validate_rows = split_records(rows, holdout_stride=holdout_stride)
    if not profile_id:
        exemplar = train_rows[0]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        profile_id = f"{exemplar.get('node_id', 'growlab')}-{stamp}"

    profile = build_profile(
        profile_id=profile_id,
        training_records=train_rows,
        validation_records=validate_rows,
        regression_type=regression,
        ridge_alpha=ridge_alpha,
        notes=notes,
    )
    save_profile(Path(profile_out), profile)

    click.echo(f"Saved profile: {profile_out}")
    click.echo(f"  profile_id: {profile.profile_id}")
    click.echo(f"  train:      {profile.training_sample_count}")
    click.echo(f"  validate:   {profile.validation_sample_count}")
    click.echo(f"  rmse:       {profile.metrics.rmse} umol/m2/s")
    click.echo(f"  mae:        {profile.metrics.mae} umol/m2/s")


@as7341_group.command("validate")
@click.option("--session", "session_path", required=True, type=click.Path(exists=True))
@click.option("--profile", "profile_path", required=True, type=click.Path(exists=True))
@click.option("--report-out", required=True, type=click.Path())
@click.option("--holdout-stride", default=4, type=int)
def validate_profile(session_path: str, profile_path: str, report_out: str, holdout_stride: int) -> None:
    """Validate an AS7341 profile against held-out session rows."""
    rows = [_coerce_record(row) for row in read_capture_rows(Path(session_path))]
    _, validate_rows = split_records(rows, holdout_stride=holdout_stride)
    report = build_validation_report(Path(profile_path), validate_rows)
    report_path = Path(report_out)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(validation_report_markdown(report))

    click.echo(f"Saved validation report: {report_out}")
    click.echo(f"  rmse:   {report.metrics.rmse} umol/m2/s")
    click.echo(f"  mae:    {report.metrics.mae} umol/m2/s")
    click.echo(f"  median: {report.metrics.median_abs_error} umol/m2/s")
