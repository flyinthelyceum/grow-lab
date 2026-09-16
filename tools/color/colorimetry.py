"""CIE colour conversions and the CIEDE2000 difference metric.

Pure standard library. Every constant here is a published CIE or IEC value,
not a measurement of anything in this project: the sRGB primaries and transfer
curve are IEC 61966-2-1, the illuminant white points are CIE 15, the Bradford
matrix is from the CIECAM lineage, and the CIEDE2000 form is Sharma, Wu and
Dalal (2005). Nothing in this file is measurable with a tool, so nothing in it
belongs in the components library.

Conventions
-----------
* XYZ is scaled so that Y = 1.0 for the illuminant white, not 100.
* Lab is ordinary CIELAB, L in 0..100.
* An illuminant is a 3-tuple of XYZ. D50 is the profile-connection-space white
  that scanner profiling works in; D65 is sRGB's. Converting between them is a
  chromatic adaptation, not a no-op, and forgetting it is worth several dE.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

Triple = Tuple[float, float, float]

# CIE 15 2-degree observer white points, Y normalised to 1.
D50: Triple = (0.96422, 1.00000, 0.82521)
D65: Triple = (0.95047, 1.00000, 1.08883)

# CIELAB's piecewise curve. epsilon = (6/29)^3, kappa = (29/3)^3.
_EPS = 216.0 / 24389.0
_KAPPA = 24389.0 / 27.0

# sRGB, IEC 61966-2-1, D65 primaries.
_SRGB_TO_XYZ_D65 = (
    (0.4124564, 0.3575761, 0.1804375),
    (0.2126729, 0.7151522, 0.0721750),
    (0.0193339, 0.1191920, 0.9503041),
)

# Bradford cone response, the adaptation transform ICC profiles use.
_BRADFORD = (
    (0.8951, 0.2664, -0.1614),
    (-0.7502, 1.7135, 0.0367),
    (0.0389, -0.0685, 1.0296),
)


def _invert(m: Sequence[Sequence[float]]) -> Tuple[Triple, Triple, Triple]:
    """Exact 3x3 inverse.

    The published inverses of both matrices above are rounded to seven places,
    and round-tripping through a rounded pair leaves a few parts per million
    on the table — small, but it is error this file invents rather than
    measures. Inverting the forward matrix instead means the two directions
    cannot disagree by more than a float.
    """
    (a, b, c), (d, e, f), (g, h, i) = m
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    if det == 0.0:
        raise ValueError("singular matrix")
    return (
        ((e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det),
        ((f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det),
        ((d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det),
    )


def _apply(matrix: Sequence[Sequence[float]], v: Sequence[float]) -> Triple:
    return (
        matrix[0][0] * v[0] + matrix[0][1] * v[1] + matrix[0][2] * v[2],
        matrix[1][0] * v[0] + matrix[1][1] * v[1] + matrix[1][2] * v[2],
        matrix[2][0] * v[0] + matrix[2][1] * v[1] + matrix[2][2] * v[2],
    )


_XYZ_D65_TO_SRGB = _invert(_SRGB_TO_XYZ_D65)
_BRADFORD_INV = _invert(_BRADFORD)


# --------------------------------------------------------------------------
# XYZ <-> Lab
# --------------------------------------------------------------------------


def xyz_to_lab(xyz: Sequence[float], white: Triple = D50) -> Triple:
    """CIE XYZ (Y = 1 white) to CIELAB under ``white``."""

    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > _EPS else (_KAPPA * t + 16.0) / 116.0

    fx, fy, fz = (f(c / w) for c, w in zip(xyz, white))
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def lab_to_xyz(lab: Sequence[float], white: Triple = D50) -> Triple:
    """CIELAB under ``white`` back to CIE XYZ (Y = 1 white)."""
    L, a, b = lab
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    def finv(ft: float) -> float:
        t3 = ft ** 3
        return t3 if t3 > _EPS else (116.0 * ft - 16.0) / _KAPPA

    yr = (fy ** 3) if L > _KAPPA * _EPS else L / _KAPPA
    return (finv(fx) * white[0], yr * white[1], finv(fz) * white[2])


# --------------------------------------------------------------------------
# Chromatic adaptation
# --------------------------------------------------------------------------


def adapt_xyz(xyz: Sequence[float], src: Triple, dst: Triple) -> Triple:
    """Bradford-adapt XYZ from one illuminant to another.

    A no-op when ``src`` and ``dst`` are the same white. Use it whenever a
    number crosses between the D50 world of ICC profiling and the D65 world of
    sRGB; skipping it shifts neutrals blue or yellow by a visible margin.
    """
    if src == dst:
        return (xyz[0], xyz[1], xyz[2])
    s = _apply(_BRADFORD, src)
    d = _apply(_BRADFORD, dst)
    c = _apply(_BRADFORD, xyz)
    scaled = (c[0] * d[0] / s[0], c[1] * d[1] / s[1], c[2] * d[2] / s[2])
    return _apply(_BRADFORD_INV, scaled)


# --------------------------------------------------------------------------
# sRGB
# --------------------------------------------------------------------------


def srgb_to_linear(c: float) -> float:
    """One sRGB channel, 0..1 encoded, to linear light."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    """One linear-light channel, 0..1, to sRGB encoding."""
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055


def srgb_to_xyz(rgb: Sequence[float], white: Triple = D65) -> Triple:
    """sRGB 0..1 to XYZ, adapted to ``white`` (default sRGB's own D65)."""
    lin = tuple(srgb_to_linear(max(0.0, min(1.0, c))) for c in rgb)
    return adapt_xyz(_apply(_SRGB_TO_XYZ_D65, lin), D65, white)


def xyz_to_srgb(xyz: Sequence[float], white: Triple = D65) -> Triple:
    """XYZ under ``white`` to sRGB 0..1, clipped into gamut."""
    lin = _apply(_XYZ_D65_TO_SRGB, adapt_xyz(xyz, white, D65))
    return tuple(max(0.0, min(1.0, linear_to_srgb(c))) for c in lin)


def srgb_to_lab(rgb: Sequence[float], white: Triple = D65) -> Triple:
    """sRGB 0..1 straight to CIELAB under ``white``."""
    return xyz_to_lab(srgb_to_xyz(rgb, white), white)


def hex_to_srgb(value: str) -> Triple:
    """``"#F1F4F6"`` to sRGB 0..1. Accepts three or six hex digits."""
    s = value.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        raise ValueError(f"not a hex colour: {value!r}")
    return tuple(int(s[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_hex(rgb: Sequence[float]) -> str:
    """sRGB 0..1 to ``"#RRGGBB"``."""
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02X}" for c in rgb)


# --------------------------------------------------------------------------
# Difference metrics
# --------------------------------------------------------------------------


def delta_e_76(lab1: Sequence[float], lab2: Sequence[float]) -> float:
    """Plain Euclidean CIELAB distance.

    Here for comparison only. It underweights differences near the neutral
    axis, which is exactly where the dial-face cream lives, so do not judge a
    match with it.
    """
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(lab1, lab2)))


def delta_e_2000(
    lab1: Sequence[float],
    lab2: Sequence[float],
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """CIEDE2000 colour difference, in the form given by Sharma, Wu and Dalal.

    The default parametric weights are the 1:1:1 reference conditions. Graphic
    arts often use kL = 2; pass it explicitly rather than assuming it.
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar = (C1 + C2) / 2.0
    C_bar7 = C_bar ** 7
    G = 0.5 * (1.0 - math.sqrt(C_bar7 / (C_bar7 + 25.0 ** 7)))

    a1p = (1.0 + G) * a1
    a2p = (1.0 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)

    def _hue(ap: float, bp: float) -> float:
        if ap == 0.0 and bp == 0.0:
            return 0.0
        return math.degrees(math.atan2(bp, ap)) % 360.0

    h1p = _hue(a1p, b1)
    h2p = _hue(a2p, b2)

    dLp = L2 - L1
    dCp = C2p - C1p

    if C1p * C2p == 0.0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180.0:
            dhp -= 360.0
        elif dhp < -180.0:
            dhp += 360.0
    dHp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2.0)

    Lp_bar = (L1 + L2) / 2.0
    Cp_bar = (C1p + C2p) / 2.0

    if C1p * C2p == 0.0:
        hp_bar = h1p + h2p
    else:
        diff = abs(h1p - h2p)
        total = h1p + h2p
        if diff <= 180.0:
            hp_bar = total / 2.0
        elif total < 360.0:
            hp_bar = (total + 360.0) / 2.0
        else:
            hp_bar = (total - 360.0) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(hp_bar - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * hp_bar))
        + 0.32 * math.cos(math.radians(3.0 * hp_bar + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * hp_bar - 63.0))
    )

    d_theta = 30.0 * math.exp(-(((hp_bar - 275.0) / 25.0) ** 2))
    Cp_bar7 = Cp_bar ** 7
    R_C = 2.0 * math.sqrt(Cp_bar7 / (Cp_bar7 + 25.0 ** 7))
    R_T = -R_C * math.sin(math.radians(2.0 * d_theta))

    S_L = 1.0 + (0.015 * (Lp_bar - 50.0) ** 2) / math.sqrt(20.0 + (Lp_bar - 50.0) ** 2)
    S_C = 1.0 + 0.045 * Cp_bar
    S_H = 1.0 + 0.015 * Cp_bar * T

    tL = dLp / (kL * S_L)
    tC = dCp / (kC * S_C)
    tH = dHp / (kH * S_H)
    return math.sqrt(tL * tL + tC * tC + tH * tH + R_T * tC * tH)


# --------------------------------------------------------------------------
# Summary statistics
# --------------------------------------------------------------------------


def percentile(values: Iterable[float], p: float) -> float:
    """Linear-interpolated percentile, ``p`` in 0..100. Empty input is 0.0."""
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return xs[int(k)]
    return xs[lo] * (hi - k) + xs[hi] * (k - lo)
