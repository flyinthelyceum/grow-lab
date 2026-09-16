# Colour Measurement — Rev A (2026-09-16)

Two jobs in this project need a colour *number* rather than a colour impression.
The near one is the Weston dial face: `INSTRUMENT_HEAD_PLANS.md` § Making the plate
says "sample the colour off the scan", and until now there was nothing in the repo
that could. The far one is pigment — reading a tube of paint, its tint, and what
the two say about a mixture. This page covers the near one and is the floor the
far one builds on.

The instrument is the flatbed. A scanner is a colorimeter with a fixed lamp, a
fixed geometry and a fixed distance, which is most of what makes a colorimeter
expensive. What it lacks is a way to know what its three channels *mean*. A
reference chart supplies that, once, and then every scan made the same way is
measured rather than merely photographed.

## What this gets you

A patch of a scan reported as CIELAB, repeatable week to week, honest to about
**1 ΔE00** cross-validated on a good chart and a warm lamp. That is inside what a
print shop can hold anyway, so for "match this cream" it is enough.

## What it does not get you

**Spectral data.** A profiled scanner reports what *its* three channels saw under
*its* lamp, fitted to a chart. Two of its consequences matter here:

- **Metamerism survives.** Two surfaces can match under the scanner's lamp and
  part company under gallery light. The scanner cannot see this coming, because
  three numbers cannot carry a spectrum. The only fix is a spectral instrument —
  see the Nix-type build brief.
- **Optical brighteners lie.** Paper and many white paints carry OBAs that absorb
  UV and re-emit blue. The scanner's lamp has its own UV content, which is not the
  gallery's, and the chart's white patch may have a different OBA load than the
  stock being matched. A face that measures neutral on the platen can read cold on
  the wall. When a match matters, prove it on a proof print under the light it will
  live under; the number narrows the search, it does not end it.
- **The chart bounds the answer.** A 24-patch ColorChecker has nothing near the
  edge of the gamut. High-chroma pigment is exactly where a 3×3 fitted to it is
  weakest, and the cross-validated error below will say so if you feed it one.

## Kit

| Item | Note |
|---|---|
| Calibrite ColorChecker Classic (24 patch) or Passport | ~$70–100. The Passport's smaller patches are fine at 600 dpi and it closes, which keeps it clean. |
| The chart's reference values | A `.cie` / `.txt` of the chart's Lab or XYZ. Batch-specific data from the maker if you have it; the generic ColorChecker data shipped with ArgyllCMS otherwise. Generic data is a floor, not a ceiling — it describes the average of a production run, not your card. |
| Epson V600 | Set up per the scanning best-practice note: lamp warmed, platen clean, every automatic off. |
| Matte black cardstock | Backing, so nothing bounces back through a thin subject. |
| A dark drawer | The chart fades. Kept in the light it is a two-year consumable; kept dark, longer. Replace it when the white patch yellows. |

No colour-management stack is required for the workflow below. ArgyllCMS is
optional and covered at the end.

## The scan

One pass, both objects. **The chart and the subject go on the platen together and
neither moves between them.** The whole method rests on the chart having seen the
same lamp, the same exposure and the same instant of the carriage's travel as the
thing being measured; two passes with a gap in between measures two different
scanners.

1. Warm the lamp — five minutes of idle scans, not thirty seconds.
2. Clean the platen, then the chart, with a blower and a microfibre. Dust reads as
   a bright speck; the sampler throws out the extremes, but do not make it work.
3. Every automatic **off**: colour restoration, backlight correction, dust removal,
   unsharp mask, auto exposure, descreening, and any "ICM" or "no colour
   correction" box set the same way every time. An automatic that thinks for itself
   makes each scan its own instrument.
4. **48-bit colour, 600 dpi, uncompressed TIFF.** The chart wants flatness, not
   detail — 600 is for the subject.
5. Place the chart in the middle band of the platen with its long axis along the
   sensor array, beside the subject rather than at the far end. The sensor array is
   fixed and the carriage travel drifts, so along-array is the better-behaved axis
   and the centre is the better-behaved place.
6. Weight the lid down on the chart. A chart lifted a millimetre at one corner
   reads as a gradient.

## The workflow

Three commands. They live in `tools/color/` and depend on nothing outside the
standard library and Pillow, which the project already carries.

### 1. Sample the chart

Open the scan in any viewer, read off the pixel coordinates of the centres of the
four corner patches — top-left, top-right, bottom-right, bottom-left, in the
image's own orientation — and hand them over. Everything between is interpolated.

```sh
python tools/color/sample_chart.py grid scan.tif \
    --corners 412,388 1596,392 1600,1180 408,1176 \
    --rows 4 --cols 6 \
    --ids-from ColorChecker.cie \
    -o measured.csv
```

`--ids-from` takes the patch names, in order, out of the reference file, so the
two sides pair up without anyone typing twenty-four identifiers. Each patch is
reduced by an interquartile mean over the middle half of its pixels: a dust speck,
a scratch or a glint is a handful of extreme values and gets discarded, without the
quantisation a plain median would bring.

### 2. Fit the model

```sh
python tools/color/fit_profile.py measured.csv ColorChecker.cie -o v600-2026-09-16.json
```

```
fitted 24 patches, gamma 1.947, device full scale 255

                      mean  median     p95     max
  fit                 0.71    0.63    1.44    1.68
  cross-validated     1.12    0.98    2.30    2.71

Quote the cross-validated mean. The fit row is the chart marking its own work.
```

Two rows, and the difference between them is the point.

- **fit** — how well the model reproduces the chart it was fitted to. Always
  flattering, because the chart is both the question and the answer. A 3×3 fitted
  to four patches scores a perfect zero and knows nothing.
- **cross-validated** — each patch held out in turn and scored against a model
  that never saw it. That is what happens to a colour the chart does not contain,
  which is every colour you actually want to measure. **This is the number to
  quote.**

A large gap between the two rows means the model is memorising rather than
generalising — usually a chart with too few patches, or one patch misread badly
enough to drag the matrix toward it.

What is being fitted is a per-channel gamma and a 3×3 to XYZ: the same shape as a
matrix-and-curves ICC profile, which is what a flatbed deserves. Gamma is found by
sweeping a bounded range rather than by a solver, because the objective is a mean
of ΔE00 values and is not smooth.

### 3. Read the subject

```sh
python tools/color/sample_chart.py points scan.tif \
    --point cream:2040,910 \
    --point cream-edge:2180,1015 \
    --point ring:2105,880 \
    --model v600-2026-09-16.json
```

```
spot                  L*      a*      b*  sRGB      device RGB
cream              84.31    1.94   13.62  #E4D3B4    221.4  204.7  175.2
cream-edge         83.02    2.11   14.40  #E1CFAE    218.0  201.2  170.9
ring               22.85    1.02    2.71  #3B3733     58.9   55.0   50.4
```

Sample the same colour in three places. If the three land within about 0.5 ΔE00 of
each other the number is real; if they spread, the surface is not uniform and the
question "what colour is it" does not have one answer.

The hex is an sRGB approximation for looking at on a screen, not the measurement.
**Give the print shop the Lab.**

### Scoring a measurement against a reference

`check_profile.py` scores any two patch sets against each other in CIEDE2000 — a
verification chart against its reference values, this month's scan against last
month's, a proof print against the target.

```sh
python tools/color/check_profile.py verify.csv ColorChecker.cie
```

It reports the mean, median, 95th percentile and worst ΔE00, lists the worst
patches with the error split into lightness, chroma and hue, and exits non-zero
when a limit is passed, so it can gate a script. The default limits — mean 2.0,
95th 4.0, max 5.0 — are this project's choice, not a standard.

The three-way split is the useful part. A miss that is all `dL` is exposure or lamp
output. A miss that is all `dC` in one direction is usually the white point. A miss
that is scattered in `dH` with the others small is a genuinely bad fit.

The tool also names a systematic bias when the whole chart leans one way, because
that is a scanner-setting problem rather than a profile problem and the fix is
upstream.

## Why not ΔE76

Because it would flatter exactly the colour this project cares about. Take the pair
(50, 2.5, 0) and (50, 0, −2.5): ΔE76 calls it 3.54, ΔE2000 calls it 4.31. Near the
neutral axis — where a cream lives — the plain Euclidean distance understates what
the eye does. `delta_e_76` is in the module for comparison; do not judge a match
with it.

## Repeating it

The model is dated and kept. Re-fit when any of these changes:

- the scanner, its driver, or any setting in the driver
- the lamp, including simply getting older — re-fit every few months
- the chart

A quick check without a full re-fit: scan the chart, sample it, and run
`check_profile.py` on the result against the reference. If the numbers have moved,
so has the scanner.

## If you want an ICC profile

The workflow above produces a number, not a profile. If you want something other
software can use, ArgyllCMS is the free path: `scanin` locates the chart in the
scan and writes a `.ti3` of device values against reference values, and `colprof`
fits a profile from it. `profcheck` reports the fit residual.

Two notes worth having before starting. First, the `.ti3` that `scanin` writes
already contains the reference values it was given, so scoring that file against
the same reference reports zero and means nothing — a profile has to be checked
against a chart it was not fitted to, or with `profcheck`, which knows the
difference. Second, a cLUT profile from `colprof` will beat a 3×3 on a chart with
saturated patches, which is the case for pigment work and not the case for a cream.

The exact flags move between Argyll versions; read `scanin -?` on the install
rather than trusting a command line copied from anywhere, this page included.

## Files

| Path | What it is |
|---|---|
| `tools/color/colorimetry.py` | XYZ/Lab, sRGB, Bradford adaptation, ΔE00 and ΔE76. Standard library only. |
| `tools/color/cgats.py` | Reads CGATS (`.ti3`, `.cie`) and plain CSV patch lists. |
| `tools/color/sample_chart.py` | `grid` samples a chart, `points` samples named spots. Pillow. |
| `tools/color/fit_profile.py` | Fits gamma + 3×3, reports fit and cross-validated error, writes the model. |
| `tools/color/check_profile.py` | Scores measured against reference in ΔE00. |
| `tests/unit/test_color.py` | The whole Sharma/Wu/Dalal CIEDE2000 table, plus the conversions. |
| `tests/unit/test_color_fit.py` | Synthetic scans whose transform is known, fitted back. |

The ΔE00 implementation is asserted against all thirty-four of the Sharma, Wu and
Dalal test pairs — the ones written to catch hue-angle wraparound and the neutral
degenerate cases, which is where every wrong implementation of this formula is
wrong. If those ever drift, the metric is broken, not imprecise.

## Open items

- **No chart in hand.** Everything above is runnable and tested against synthetic
  scans; none of it has yet seen a real ColorChecker. The first real chart will
  settle whether the V600's cross-validated error lands near 1 or near 2.
- **The cream is still unmeasured.** The dial scans exist; the number does not.
  This is the tool for it, waiting on the chart.
- **Nothing here reads spectra.** The pigment work needs that, and the scanner
  cannot be made to do it. That is a separate instrument, and its own brief.
