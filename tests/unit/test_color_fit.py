"""The fitter and the sampler, held against data whose answer is known.

A colour fit is the kind of code that always produces a plausible-looking
number, so the tests here generate scans from a transform they choose and
check that the fit recovers it. If the fitter can not recover a transform it
was handed directly, nothing it says about a real scanner means anything.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.color.cgats import load, parse_csv  # noqa: E402
from tools.color.colorimetry import D50, _apply, delta_e_2000, xyz_to_lab  # noqa: E402
from tools.color.fit_profile import (  # noqa: E402
    MODEL_KIND,
    FitError,
    Model,
    build,
    cross_validate,
    detect_scale,
    fit,
)
from tools.color.fit_profile import main as fit_main  # noqa: E402
from tools.color.sample_chart import (  # noqa: E402
    SampleError,
    default_ids,
    grid_centres,
    interquartile_mean,
    sample_box,
)
from tools.color.sample_chart import main as sample_main  # noqa: E402

PIL = pytest.importorskip("PIL.Image")

# A plausible scanner: a gamma near 2.0 and a matrix that is sRGB's own,
# nudged so it is not the identity case and not symmetric.
TRUE_GAMMA = 1.94
TRUE_MATRIX = [
    [0.4360, 0.3851, 0.1431],
    [0.2225, 0.7169, 0.0606],
    [0.0139, 0.0971, 0.7141],
]

# Twenty-four device RGB values spread over the cube, the way a chart is.
DEVICE_RGB = [
    (0.15, 0.10, 0.08), (0.60, 0.45, 0.38), (0.30, 0.38, 0.52), (0.25, 0.32, 0.15),
    (0.42, 0.40, 0.60), (0.35, 0.68, 0.62), (0.75, 0.38, 0.12), (0.22, 0.25, 0.58),
    (0.65, 0.25, 0.28), (0.20, 0.13, 0.30), (0.55, 0.70, 0.18), (0.80, 0.55, 0.10),
    (0.12, 0.15, 0.48), (0.22, 0.48, 0.20), (0.55, 0.14, 0.15), (0.88, 0.72, 0.08),
    (0.62, 0.24, 0.48), (0.10, 0.42, 0.55), (0.96, 0.96, 0.95), (0.78, 0.78, 0.78),
    (0.60, 0.60, 0.60), (0.42, 0.42, 0.42), (0.26, 0.26, 0.26), (0.12, 0.12, 0.12),
]


def _truth_lab(rgb):
    lin = [c ** TRUE_GAMMA for c in rgb]
    return xyz_to_lab(_apply(TRUE_MATRIX, lin), D50)


REFERENCE_LAB = [_truth_lab(p) for p in DEVICE_RGB]
IDS = [f"{'ABCD'[i // 6]}{i % 6 + 1}" for i in range(24)]


def _reference_csv() -> str:
    rows = ["id,L,a,b"]
    for ident, lab in zip(IDS, REFERENCE_LAB):
        rows.append(f"{ident},{lab[0]:.6f},{lab[1]:.6f},{lab[2]:.6f}")
    return "\n".join(rows) + "\n"


def _measured_csv(scale: float = 255.0) -> str:
    rows = ["SAMPLE_ID,RGB_R,RGB_G,RGB_B"]
    for ident, rgb in zip(IDS, DEVICE_RGB):
        rows.append(f"{ident},{rgb[0]*scale:.6f},{rgb[1]*scale:.6f},{rgb[2]*scale:.6f}")
    return "\n".join(rows) + "\n"


class TestFit:
    def test_recovers_the_transform_it_was_given(self):
        gamma, matrix = fit(DEVICE_RGB, REFERENCE_LAB)
        assert gamma == pytest.approx(TRUE_GAMMA, abs=0.01)
        for got_row, want_row in zip(matrix, TRUE_MATRIX):
            assert got_row == pytest.approx(want_row, abs=1e-3)

    def test_residual_is_negligible_on_exact_data(self):
        gamma, matrix = fit(DEVICE_RGB, REFERENCE_LAB)
        lin = [tuple(c ** gamma for c in p) for p in DEVICE_RGB]
        errs = [
            delta_e_2000(lab, xyz_to_lab(_apply(matrix, p), D50))
            for p, lab in zip(lin, REFERENCE_LAB)
        ]
        assert max(errs) < 0.05

    def test_fixed_gamma_is_honoured(self):
        gamma, _ = fit(DEVICE_RGB, REFERENCE_LAB, gamma=2.2)
        assert gamma == 2.2

    def test_too_few_patches(self):
        with pytest.raises(FitError):
            fit(DEVICE_RGB[:3], REFERENCE_LAB[:3])

    def test_degenerate_chart(self):
        # Every patch the same colour: the normal equations go singular.
        with pytest.raises(FitError):
            fit([(0.5, 0.5, 0.5)] * 6, [_truth_lab((0.5, 0.5, 0.5))] * 6)


class TestCrossValidation:
    def test_one_value_per_patch(self):
        gamma, _ = fit(DEVICE_RGB, REFERENCE_LAB)
        assert len(cross_validate(DEVICE_RGB, REFERENCE_LAB, gamma)) == len(DEVICE_RGB)

    def test_exact_data_generalises(self):
        gamma, _ = fit(DEVICE_RGB, REFERENCE_LAB)
        assert max(cross_validate(DEVICE_RGB, REFERENCE_LAB, gamma)) < 0.2

    def test_a_bad_patch_shows_up_held_out_not_in_the_fit(self):
        # Corrupt one reference patch. The full fit absorbs some of the error
        # into the matrix; the held-out fold cannot, so it reports more.
        labs = list(REFERENCE_LAB)
        labs[7] = (labs[7][0] + 12.0, labs[7][1] - 9.0, labs[7][2] + 7.0)
        gamma, matrix = fit(DEVICE_RGB, labs)
        lin = tuple(c ** gamma for c in DEVICE_RGB[7])
        in_fit = delta_e_2000(labs[7], xyz_to_lab(_apply(matrix, lin), D50))
        held_out = cross_validate(DEVICE_RGB, labs, gamma)[7]
        assert held_out > in_fit


class TestDetectScale:
    @pytest.mark.parametrize(
        "top,expected", [(0.98, 1.0), (99.5, 100.0), (250.0, 255.0), (60000.0, 65535.0)]
    )
    def test_bands(self, top, expected):
        assert detect_scale([0.0, top]) == expected

    def test_empty(self):
        assert detect_scale([]) == 1.0


class TestBuild:
    def test_end_to_end(self):
        measured = parse_csv(_measured_csv(), "m")
        reference = parse_csv(_reference_csv(), "r")
        model, missing = build(measured, reference)
        assert missing == []
        assert model.kind == MODEL_KIND
        assert model.rgb_scale == 255.0
        assert model.gamma == pytest.approx(TRUE_GAMMA, abs=0.01)
        assert model.fit["cross_validated"]["mean"] < 0.2

    def test_scale_is_irrelevant_to_the_result(self):
        a, _ = build(parse_csv(_measured_csv(255.0), "m"), parse_csv(_reference_csv(), "r"))
        b, _ = build(parse_csv(_measured_csv(100.0), "m"), parse_csv(_reference_csv(), "r"))
        assert a.gamma == pytest.approx(b.gamma, abs=1e-6)

    def test_unmatched_measured_patches_are_dropped(self):
        extra = _measured_csv() + "ZZ,10,10,10\n"
        model, missing = build(parse_csv(extra, "m"), parse_csv(_reference_csv(), "r"))
        assert missing == ["ZZ"]
        assert model.fit["fit"]["n"] == 24

    def test_measured_without_device_rgb_raises(self):
        with pytest.raises(FitError, match="no device RGB"):
            build(parse_csv(_reference_csv(), "m"), parse_csv(_reference_csv(), "r"))

    def test_no_shared_identifiers_raises(self):
        other = "SAMPLE_ID,RGB_R,RGB_G,RGB_B\nZZ,10,10,10\nYY,20,20,20\n"
        with pytest.raises(FitError, match="no patches paired"):
            build(parse_csv(other, "m"), parse_csv(_reference_csv(), "r"))


class TestModel:
    def _model(self):
        return build(parse_csv(_measured_csv(), "m"), parse_csv(_reference_csv(), "r"))[0]

    def test_to_lab_matches_the_truth(self):
        model = self._model()
        for rgb, lab in zip(DEVICE_RGB, REFERENCE_LAB):
            assert delta_e_2000(lab, model.to_lab(rgb)) < 0.2

    def test_to_hex(self):
        model = self._model()
        assert model.to_hex((0.96, 0.96, 0.95)).startswith("#")
        assert len(model.to_hex((0.5, 0.5, 0.5))) == 7

    def test_clamps_out_of_range_input(self):
        model = self._model()
        assert model.to_lab((-0.5, 2.0, 0.5))[0] >= 0.0

    def test_roundtrip_through_json(self, tmp_path):
        model = self._model()
        path = tmp_path / "m.json"
        model.dump(path)
        back = Model.load(path)
        assert back.gamma == model.gamma
        assert back.to_lab((0.5, 0.4, 0.3)) == pytest.approx(model.to_lab((0.5, 0.4, 0.3)))

    def test_rejects_a_foreign_json(self, tmp_path):
        path = tmp_path / "x.json"
        path.write_text(json.dumps({"kind": "something else"}), encoding="utf-8")
        with pytest.raises(ValueError):
            Model.load(path)


class TestFitCli:
    def _files(self, tmp_path):
        m = tmp_path / "m.csv"
        r = tmp_path / "r.csv"
        m.write_text(_measured_csv(), encoding="utf-8")
        r.write_text(_reference_csv(), encoding="utf-8")
        return str(m), str(r)

    def test_reports_both_rows(self, tmp_path, capsys):
        m, r = self._files(tmp_path)
        assert fit_main([m, r]) == 0
        out = capsys.readouterr().out
        assert "cross-validated" in out
        assert "fit" in out

    def test_writes_a_model(self, tmp_path):
        m, r = self._files(tmp_path)
        out = tmp_path / "v600.json"
        assert fit_main([m, r, "-o", str(out)]) == 0
        assert Model.load(out).kind == MODEL_KIND

    def test_json_mode(self, tmp_path, capsys):
        m, r = self._files(tmp_path)
        assert fit_main([m, r, "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["kind"] == MODEL_KIND

    def test_bad_input_exits_two(self, tmp_path, capsys):
        m, r = self._files(tmp_path)
        assert fit_main([r, r]) == 2
        assert "fit_profile" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# The sampler
# ---------------------------------------------------------------------------

PATCH = 40
GAP = 8
MARGIN = 30


def _chart_image(rows: int = 4, cols: int = 6, dust: bool = False):
    """Draw a synthetic chart whose patch colours are known exactly."""
    from PIL import Image, ImageDraw

    w = MARGIN * 2 + cols * PATCH + (cols - 1) * GAP
    h = MARGIN * 2 + rows * PATCH + (rows - 1) * GAP
    im = Image.new("RGB", (w, h), (0, 0, 0))
    draw = ImageDraw.Draw(im)
    for r in range(rows):
        for c in range(cols):
            rgb = tuple(round(v * 255) for v in DEVICE_RGB[r * cols + c])
            x = MARGIN + c * (PATCH + GAP)
            y = MARGIN + r * (PATCH + GAP)
            draw.rectangle([x, y, x + PATCH - 1, y + PATCH - 1], fill=rgb)
            if dust:
                # A speck and a scratch, right in the sampled box.
                draw.point((x + PATCH // 2, y + PATCH // 2), fill=(255, 255, 255))
                draw.line([(x + 14, y + 14), (x + 20, y + 20)], fill=(0, 0, 0))
    return im


def _corner_centres(rows: int = 4, cols: int = 6):
    half = PATCH / 2.0

    def centre(r, c):
        return (
            MARGIN + c * (PATCH + GAP) + half,
            MARGIN + r * (PATCH + GAP) + half,
        )

    return [centre(0, 0), centre(0, cols - 1), centre(rows - 1, cols - 1), centre(rows - 1, 0)]


class TestInterquartileMean:
    def test_plain_case(self):
        assert interquartile_mean([1, 2, 3, 4, 5, 6, 7, 8]) == pytest.approx(4.5)

    def test_rejects_outliers(self):
        clean = [10.0] * 20
        dirty = clean + [255.0, 255.0, 0.0, 0.0]
        assert interquartile_mean(dirty) == pytest.approx(10.0)

    def test_short_input_falls_back_to_the_mean(self):
        assert interquartile_mean([2.0, 4.0]) == pytest.approx(3.0)

    def test_empty_raises(self):
        with pytest.raises(SampleError):
            interquartile_mean([])


class TestGridGeometry:
    def test_centres_of_a_square_grid(self):
        centres = grid_centres([(0, 0), (10, 0), (10, 10), (0, 10)], 3, 3)
        assert len(centres) == 9
        assert centres[0] == pytest.approx((0.0, 0.0))
        assert centres[4] == pytest.approx((5.0, 5.0))
        assert centres[8] == pytest.approx((10.0, 10.0))

    def test_handles_rotation(self):
        # The same grid turned a quarter turn: centres follow the corners.
        centres = grid_centres([(0, 10), (0, 0), (10, 0), (10, 10)], 3, 3)
        assert centres[4] == pytest.approx((5.0, 5.0))

    def test_wrong_corner_count(self):
        with pytest.raises(SampleError):
            grid_centres([(0, 0), (1, 0), (1, 1)], 2, 2)

    def test_degenerate_grid(self):
        with pytest.raises(SampleError):
            grid_centres([(0, 0), (1, 0), (1, 1), (0, 1)], 1, 4)

    def test_default_ids(self):
        ids = default_ids(4, 6)
        assert ids[0] == "A1"
        assert ids[-1] == "D6"
        assert len(ids) == 24


class TestSampleBox:
    def test_reads_a_flat_patch(self):
        im = _chart_image()
        centre = _corner_centres()[0]
        rgb = sample_box(im, centre, 10, 10)
        assert rgb == pytest.approx(tuple(round(v * 255) for v in DEVICE_RGB[0]), abs=0.5)

    def test_survives_dust(self):
        rgb = sample_box(_chart_image(dust=True), _corner_centres()[0], 10, 10)
        assert rgb == pytest.approx(tuple(round(v * 255) for v in DEVICE_RGB[0]), abs=0.5)

    def test_off_image_raises(self):
        with pytest.raises(SampleError):
            sample_box(_chart_image(), (-500, -500), 5, 5)


class TestSampleCli:
    def _scan(self, tmp_path, dust: bool = False) -> str:
        path = tmp_path / "scan.png"
        _chart_image(dust=dust).save(path)
        return str(path)

    def _corner_args(self):
        return [f"{x:.1f},{y:.1f}" for x, y in _corner_centres()]

    def test_grid_round_trips_into_a_fit(self, tmp_path, capsys):
        scan = self._scan(tmp_path, dust=True)
        measured = tmp_path / "measured.csv"
        ref = tmp_path / "ref.csv"
        ref.write_text(_reference_csv(), encoding="utf-8")
        code = sample_main(
            ["grid", scan, "--corners", *self._corner_args(), "--rows", "4", "--cols", "6",
             "-o", str(measured)]
        )
        assert code == 0
        capsys.readouterr()

        model, missing = build(load(str(measured)), load(str(ref)))
        assert missing == []
        # 8-bit quantisation of the synthetic patches is the only error left,
        # so the fit should land well inside a just-noticeable difference.
        assert model.fit["cross_validated"]["mean"] < 1.0

    def test_grid_to_stdout(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        assert sample_main(
            ["grid", scan, "--corners", *self._corner_args(), "--rows", "4", "--cols", "6"]
        ) == 0
        out = capsys.readouterr().out
        assert out.splitlines()[0] == "SAMPLE_ID,RGB_R,RGB_G,RGB_B"
        assert len(out.strip().splitlines()) == 25

    def test_ids_from_reference(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        ref = tmp_path / "ref.csv"
        ref.write_text(_reference_csv(), encoding="utf-8")
        assert sample_main(
            ["grid", scan, "--corners", *self._corner_args(), "--rows", "4", "--cols", "6",
             "--ids-from", str(ref)]
        ) == 0
        assert ",".join(capsys.readouterr().out.splitlines()[1].split(",")[:1]) == "A1"

    def test_ids_from_too_short(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        short = tmp_path / "short.csv"
        short.write_text("id,L,a,b\nA1,50,0,0\n", encoding="utf-8")
        assert sample_main(
            ["grid", scan, "--corners", *self._corner_args(), "--rows", "4", "--cols", "6",
             "--ids-from", str(short)]
        ) == 2
        assert "names 1 patches" in capsys.readouterr().err

    def test_points_with_a_model(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        model_path = tmp_path / "m.json"
        build(parse_csv(_measured_csv(), "m"), parse_csv(_reference_csv(), "r"))[0].dump(model_path)
        x, y = _corner_centres()[0]
        assert sample_main(
            ["points", scan, "--point", f"first:{x:.0f},{y:.0f}", "--model", str(model_path),
             "--radius", "10"]
        ) == 0
        out = capsys.readouterr().out
        assert "sRGB" in out
        line = [ln for ln in out.splitlines() if ln.startswith("first")][0]
        measured_L = float(line.split()[1])
        assert measured_L == pytest.approx(REFERENCE_LAB[0][0], abs=1.0)

    def test_points_without_a_model(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        x, y = _corner_centres()[1]
        assert sample_main(["points", scan, "--point", f"p:{x:.0f},{y:.0f}"]) == 0
        assert "p" in capsys.readouterr().out

    def test_malformed_point(self, tmp_path, capsys):
        scan = self._scan(tmp_path)
        assert sample_main(["points", scan, "--point", "nocolon"]) == 2
        assert "not a name:x,y" in capsys.readouterr().err

    def test_missing_image(self, tmp_path, capsys):
        assert sample_main(
            ["grid", str(tmp_path / "nope.png"), "--corners", *self._corner_args(),
             "--rows", "4", "--cols", "6"]
        ) == 2
        assert "sample_chart" in capsys.readouterr().err
