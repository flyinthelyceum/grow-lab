"""The colour maths must be right before any of it decides a paint colour.

CIEDE2000 is notorious for looking correct and being wrong: the hue-angle
arithmetic has discontinuities at 0/360 and degenerate cases when either
sample is neutral, and an implementation that gets everything else right can
still be several units out there. Sharma, Wu and Dalal published a table of
pairs chosen to exercise exactly those cases; the whole of it is asserted
below. If one of these drifts, the metric is broken, not merely imprecise.

Reference: Sharma, Wu and Dalal, "The CIEDE2000 Color-Difference Formula",
Color Research and Application 30(1), 2005, supplementary test data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.color.cgats import CgatsError, parse_cgats, parse_csv  # noqa: E402
from tools.color.check_profile import compare, main, summarise  # noqa: E402
from tools.color.colorimetry import (  # noqa: E402
    D50,
    D65,
    adapt_xyz,
    delta_e_76,
    delta_e_2000,
    hex_to_srgb,
    lab_to_xyz,
    linear_to_srgb,
    percentile,
    srgb_to_hex,
    srgb_to_lab,
    srgb_to_linear,
    srgb_to_xyz,
    xyz_to_lab,
    xyz_to_srgb,
)

# (Lab1, Lab2, expected dE00) — the published table, in its published order.
SHARMA = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]


class TestDeltaE2000:
    @pytest.mark.parametrize("lab1,lab2,expected", SHARMA)
    def test_sharma_table(self, lab1, lab2, expected):
        assert delta_e_2000(lab1, lab2) == pytest.approx(expected, abs=1e-4)

    def test_identical_is_zero(self):
        assert delta_e_2000((42.0, -3.0, 17.0), (42.0, -3.0, 17.0)) == 0.0

    @pytest.mark.parametrize("lab1,lab2,_", SHARMA)
    def test_symmetric(self, lab1, lab2, _):
        assert delta_e_2000(lab1, lab2) == pytest.approx(delta_e_2000(lab2, lab1), abs=1e-9)

    def test_both_neutral_does_not_divide_by_zero(self):
        # C1' * C2' == 0 is the branch that crashes naive implementations.
        assert delta_e_2000((50.0, 0.0, 0.0), (60.0, 0.0, 0.0)) > 0

    def test_kl_two_relaxes_lightness_only(self):
        lightness = ((50.0, 0.0, 0.0), (55.0, 0.0, 0.0))
        hue = ((50.0, 10.0, 0.0), (50.0, 10.0, 6.0))
        assert delta_e_2000(*lightness, kL=2.0) < delta_e_2000(*lightness)
        assert delta_e_2000(*hue, kL=2.0) == pytest.approx(delta_e_2000(*hue))


class TestDeltaE76:
    def test_is_euclidean(self):
        assert delta_e_76((50.0, 0.0, 0.0), (50.0, 3.0, 4.0)) == pytest.approx(5.0)

    def test_understates_near_neutral_against_2000(self):
        # The reason the cream match is not judged on dE76: two pairs the eye
        # separates very differently score the same here.
        near_neutral = ((50.0, 2.5, 0.0), (50.0, 0.0, -2.5))
        assert delta_e_76(*near_neutral) == pytest.approx(3.5355, abs=1e-3)
        assert delta_e_2000(*near_neutral) == pytest.approx(4.3065, abs=1e-4)


class TestLabXyz:
    def test_white_is_L100(self):
        L, a, b = xyz_to_lab(D50, D50)
        assert L == pytest.approx(100.0)
        assert a == pytest.approx(0.0, abs=1e-9)
        assert b == pytest.approx(0.0, abs=1e-9)

    def test_black_is_L0(self):
        assert xyz_to_lab((0.0, 0.0, 0.0), D50)[0] == pytest.approx(0.0)

    @pytest.mark.parametrize(
        "xyz",
        [(0.2, 0.18, 0.1), (0.9, 0.95, 1.05), (0.001, 0.0008, 0.0012), (0.5, 0.5, 0.5)],
    )
    def test_roundtrip(self, xyz):
        back = lab_to_xyz(xyz_to_lab(xyz, D50), D50)
        assert back == pytest.approx(xyz, abs=1e-9)

    def test_linear_branch_below_epsilon_roundtrips(self):
        # Very dark values take the linear leg of the piecewise curve; the
        # inverse has to take the same leg or near-black drifts.
        dark = (0.0002, 0.0002, 0.0002)
        assert lab_to_xyz(xyz_to_lab(dark, D50), D50) == pytest.approx(dark, abs=1e-12)


class TestAdaptation:
    def test_same_white_is_identity(self):
        xyz = (0.3, 0.25, 0.4)
        assert adapt_xyz(xyz, D50, D50) == pytest.approx(xyz)

    def test_white_maps_to_white(self):
        assert adapt_xyz(D65, D65, D50) == pytest.approx(D50, abs=1e-4)

    def test_roundtrip(self):
        xyz = (0.3, 0.25, 0.4)
        there = adapt_xyz(xyz, D50, D65)
        assert adapt_xyz(there, D65, D50) == pytest.approx(xyz, abs=1e-9)

    def test_is_not_a_no_op(self):
        # Skipping adaptation is worth real error, which is why it exists.
        under_d50 = xyz_to_lab((0.5, 0.5, 0.5), D50)
        naive = xyz_to_lab((0.5, 0.5, 0.5), D65)
        assert delta_e_2000(under_d50, naive) > 2.0


class TestSrgb:
    def test_transfer_curve_roundtrip(self):
        for v in (0.0, 0.001, 0.04, 0.5, 0.9, 1.0):
            assert linear_to_srgb(srgb_to_linear(v)) == pytest.approx(v, abs=1e-12)

    def test_white_is_white(self):
        assert srgb_to_xyz((1.0, 1.0, 1.0), D65) == pytest.approx(D65, abs=1e-4)
        L, a, b = srgb_to_lab((1.0, 1.0, 1.0), D65)
        assert L == pytest.approx(100.0, abs=1e-3)
        assert (a, b) == pytest.approx((0.0, 0.0), abs=1e-3)

    def test_midgrey_lightness(self):
        # 50% sRGB grey lands near L* 53.4, not 50 — the transfer curve, not a bug.
        assert srgb_to_lab((0.5, 0.5, 0.5), D65)[0] == pytest.approx(53.39, abs=0.02)

    @pytest.mark.parametrize("rgb", [(0.2, 0.4, 0.6), (1.0, 0.0, 0.0), (0.0, 0.0, 0.0)])
    def test_xyz_roundtrip(self, rgb):
        assert xyz_to_srgb(srgb_to_xyz(rgb, D50), D50) == pytest.approx(rgb, abs=1e-9)

    def test_hex(self):
        assert hex_to_srgb("#F1F4F6") == pytest.approx((241 / 255, 244 / 255, 246 / 255))
        assert hex_to_srgb("0F6") == hex_to_srgb("#00FF66")
        assert srgb_to_hex(hex_to_srgb("#0F6F7D")) == "#0F6F7D"

    def test_bad_hex_raises(self):
        with pytest.raises(ValueError):
            hex_to_srgb("#12345")


class TestPercentile:
    def test_endpoints(self):
        xs = [1.0, 2.0, 3.0, 4.0]
        assert percentile(xs, 0.0) == 1.0
        assert percentile(xs, 100.0) == 4.0

    def test_interpolates(self):
        assert percentile([0.0, 10.0], 50.0) == pytest.approx(5.0)

    def test_degenerate(self):
        assert percentile([], 95.0) == 0.0
        assert percentile([7.0], 95.0) == 7.0


TI3 = """\
CGATS.17
DESCRIPTOR "Argyll Calibration Target chart information 3"
KEYWORD "DEVICE_CLASS"
DEVICE_CLASS "INPUT"

NUMBER_OF_FIELDS 7
BEGIN_DATA_FORMAT
SAMPLE_ID RGB_R RGB_G RGB_B XYZ_X XYZ_Y XYZ_Z
END_DATA_FORMAT

NUMBER_OF_SETS 3
BEGIN_DATA
A1 38.2 25.1 19.4 11.0 9.9 6.3
A2 65.0 58.0 52.0 36.0 36.5 33.0
A3 96.4 96.0 95.0 88.0 91.0 76.0
END_DATA
"""

CIE = """\
CGATS.17
BEGIN_DATA_FORMAT
SAMPLE_ID LAB_L LAB_A LAB_B
END_DATA_FORMAT
BEGIN_DATA
A1 37.99 13.56 14.06
A2 66.68 0.43 0.09
A3 96.54 -0.43 1.19
END_DATA
"""


class TestCgats:
    def test_reads_ti3_and_derives_lab_from_xyz(self):
        ps = parse_cgats(TI3, "ti3")
        assert len(ps) == 3
        assert [p.ident for p in ps.patches] == ["A1", "A2", "A3"]
        # XYZ arrives on a 0..100 scale and must be normalised before Lab.
        assert ps.patches[2].xyz == pytest.approx((0.88, 0.91, 0.76))
        assert ps.patches[2].lab[0] == pytest.approx(xyz_to_lab((0.88, 0.91, 0.76), D50)[0])
        assert ps.patches[0].rgb == pytest.approx((38.2, 25.1, 19.4))

    def test_reads_lab_directly(self):
        ps = parse_cgats(CIE, "cie")
        assert ps.patches[0].lab == pytest.approx((37.99, 13.56, 14.06))
        assert ps.patches[0].xyz is None

    def test_by_id(self):
        assert set(parse_cgats(CIE, "cie").by_id()) == {"A1", "A2", "A3"}

    def test_csv_with_aliases(self):
        ps = parse_csv("id,L,a,b\nA1,37.99,13.56,14.06\nA2,66.68,0.43,0.09\n", "csv")
        assert len(ps) == 2
        assert ps.patches[1].lab == pytest.approx((66.68, 0.43, 0.09))

    def test_device_only_file_has_no_colorimetry(self):
        ps = parse_csv("SAMPLE_ID,RGB_R,RGB_G,RGB_B\nA1,38.2,25.1,19.4\n", "dev")
        assert ps.patches[0].lab is None
        assert ps.patches[0].rgb == pytest.approx((38.2, 25.1, 19.4))
        assert ps.has_colorimetry() is False
        assert parse_cgats(CIE, "cie").has_colorimetry() is True

    def test_missing_colour_columns_raises(self):
        with pytest.raises(CgatsError):
            parse_csv("id,notes\nA1,hello\n", "csv")

    def test_short_row_raises(self):
        bad = CIE.replace("A2 66.68 0.43 0.09", "A2 66.68 0.43")
        with pytest.raises(CgatsError):
            parse_cgats(bad, "cie")

    def test_no_data_block_raises(self):
        with pytest.raises(CgatsError):
            parse_cgats("DESCRIPTOR \"nothing here\"\n", "empty")


class TestCompare:
    def test_pairs_by_identifier(self):
        rows, missing = compare(parse_cgats(TI3, "m"), parse_cgats(CIE, "r"))
        assert [r.ident for r in rows] == ["A1", "A2", "A3"]
        assert missing == []

    def test_reports_unmeasured_patches(self):
        short = parse_csv("id,L,a,b\nA1,37.99,13.56,14.06\n", "m")
        rows, missing = compare(short, parse_cgats(CIE, "r"))
        assert len(rows) == 1
        assert missing == ["A2", "A3"]

    def test_perfect_match_is_zero(self):
        ref = parse_cgats(CIE, "r")
        rows, _ = compare(ref, ref)
        assert all(r.de == 0.0 for r in rows)

    def test_splits_lightness_from_chroma(self):
        ref = parse_csv("id,L,a,b\nP,50,20,0\n", "r")
        lighter = parse_csv("id,L,a,b\nP,55,20,0\n", "m")
        rows, _ = compare(lighter, ref)
        assert rows[0].dL == pytest.approx(5.0)
        assert rows[0].dC == pytest.approx(0.0)
        assert rows[0].dH == pytest.approx(0.0, abs=1e-9)

        duller = parse_csv("id,L,a,b\nP,50,12,0\n", "m")
        rows, _ = compare(duller, ref)
        assert rows[0].dC == pytest.approx(-8.0)
        assert rows[0].dL == pytest.approx(0.0)

    def test_hue_error_is_signed(self):
        ref = parse_csv("id,L,a,b\nP,50,20,0\n", "r")
        one_way, _ = compare(parse_csv("id,L,a,b\nP,50,20,6\n", "m"), ref)
        other, _ = compare(parse_csv("id,L,a,b\nP,50,20,-6\n", "m"), ref)
        assert one_way[0].dH > 0
        assert other[0].dH < 0


class TestSummarise:
    def test_stats(self):
        ref = parse_cgats(CIE, "r")
        rows, _ = compare(ref, ref)
        stats = summarise(rows)
        assert stats["n"] == 3
        assert stats["max"] == 0.0

    def test_empty(self):
        assert summarise([])["n"] == 0


class TestCli:
    def _write(self, tmp_path, name, text):
        p = tmp_path / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_pass_exits_zero(self, tmp_path, capsys):
        ref = self._write(tmp_path, "ref.cie", CIE)
        code = main([ref, ref])
        assert code == 0
        assert "PASS" in capsys.readouterr().out

    def test_over_limit_exits_one(self, tmp_path, capsys):
        ref = self._write(tmp_path, "ref.cie", CIE)
        off = self._write(
            tmp_path,
            "off.csv",
            "id,L,a,b\nA1,50,13.56,14.06\nA2,66.68,0.43,0.09\nA3,96.54,-0.43,1.19\n",
        )
        assert main([off, ref]) == 1
        assert "FAIL" in capsys.readouterr().out

    def test_thresholds_are_settable(self, tmp_path):
        ref = self._write(tmp_path, "ref.cie", CIE)
        off = self._write(
            tmp_path,
            "off.csv",
            "id,L,a,b\nA1,50,13.56,14.06\nA2,66.68,0.43,0.09\nA3,96.54,-0.43,1.19\n",
        )
        assert main([off, ref, "--mean", "50", "--p95", "50", "--max", "50"]) == 0

    def test_json_output(self, tmp_path, capsys):
        import json

        ref = self._write(tmp_path, "ref.cie", CIE)
        main([ref, ref, "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert payload["stats"]["n"] == 3
        assert payload["failed"] == []
        assert len(payload["patches"]) == 3

    def test_no_shared_identifiers_exits_two(self, tmp_path, capsys):
        ref = self._write(tmp_path, "ref.cie", CIE)
        other = self._write(tmp_path, "other.csv", "id,L,a,b\nZ9,50,0,0\n")
        assert main([other, ref]) == 2
        assert "no patches paired" in capsys.readouterr().err

    def test_device_only_input_exits_two_with_a_pointer(self, tmp_path, capsys):
        ref = self._write(tmp_path, "ref.cie", CIE)
        dev = self._write(
            tmp_path, "dev.csv", "SAMPLE_ID,RGB_R,RGB_G,RGB_B\nA1,38.2,25.1,19.4\n"
        )
        assert main([dev, ref]) == 2
        assert "fit_profile" in capsys.readouterr().err

    def test_missing_file_exits_two(self, tmp_path, capsys):
        ref = self._write(tmp_path, "ref.cie", CIE)
        assert main([str(tmp_path / "nope.cie"), ref]) == 2
        assert "check_profile" in capsys.readouterr().err
