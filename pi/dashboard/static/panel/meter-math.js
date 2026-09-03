/**
 * Needle maths — a line-for-line mirror of pi/services/meters.py.
 *
 * The emulator is only worth anything if it moves the way the hardware moves.
 * If this file drifts from the Python, the panel on screen will read plausibly
 * while the panel on the mast reads differently, and nobody would notice until
 * the meters were mounted.
 *
 * So this is not an approximation and not a redrawing. Every function here has
 * a counterpart in the service, and tests/unit/test_panel_math_parity.py runs
 * this module under node against the Python across a sweep of inputs. Change
 * one side without the other and that test fails.
 *
 * ES module, no dependencies, so node can import it directly.
 */

/** Map a sensor value to -1.0 .. +1.0 about its target. */
export function normalise(value, centre, span) {
  if (span <= 0) return 0.0;
  return Math.max(-1.0, Math.min(1.0, (value - centre) / span));
}

/**
 * Piecewise-linear correction of a normalised deflection.
 * `points` are [commanded, actual] pairs in ascending commanded order.
 */
export function applyCalibration(x, points) {
  if (!points || points.length < 2) return x;

  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);

  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];

  for (let i = 0; i < xs.length - 1; i += 1) {
    const x0 = xs[i];
    const x1 = xs[i + 1];
    if (x0 <= x && x <= x1) {
      if (x1 === x0) return ys[i];
      const t = (x - x0) / (x1 - x0);
      return ys[i] + t * (ys[i + 1] - ys[i]);
    }
  }
  return x;
}

/** Exponential smoothing factor for a step of `dt` toward a target. */
export function easeAlpha(dt, timeConstant) {
  if (timeConstant <= 0) return 1.0;
  return 1.0 - Math.exp(-dt / timeConstant);
}

/** Clamp a DAC code into the 12-bit range. Mirrors mcp4728.clamp_code. */
export function clampCode(code) {
  return Math.max(0, Math.min(0xfff, Math.trunc(code)));
}

/**
 * Codes for a differential pair from a normalised deflection.
 * Mirrors mcp4728.differential_codes, including Python's round-half-to-even.
 */
export function differentialCodes(x, midpoint = 0x800, spanCounts = 0x800) {
  const clamped = Math.max(-1.0, Math.min(1.0, x));
  const delta = clamped * spanCounts;
  return [
    clampCode(bankersRound(midpoint + delta)),
    clampCode(bankersRound(midpoint - delta)),
  ];
}

/**
 * Python's round(): half-to-even, not half-away-from-zero like Math.round.
 * Matters here because midpoint ± delta lands exactly on .5 for round spans,
 * and a one-count disagreement is a visible needle offset at the endpoints.
 */
export function bankersRound(value) {
  const floor = Math.floor(value);
  const diff = value - floor;
  if (diff > 0.5) return floor + 1;
  if (diff < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}
