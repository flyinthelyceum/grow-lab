/**
 * Centre-zero dial rendering for the panel emulator.
 *
 * Draws a 3-1/2 in moving-coil movement the way the Weston 301 reads: zero at
 * top centre, deflection either side, needle pivoting low in the case with the
 * scale arc above it.
 *
 * What is faithful and what is not:
 *
 * Coordinates here are **screen space** (y down). The caller converts panel
 * inches to screen inches once, so nothing in this file has to be mirrored and
 * text needs no unflipping.
 *
 * - Bezel OD (3.50 in) is nominal for the size class and safe.
 * - The **sweep angle** is a visual property of the movement and has not been
 *   measured. 90 degrees total is typical for the class and is the default;
 *   it is exposed as a control precisely because it changes legibility and we
 *   do not yet know the real figure.
 * - Scale numbers come from the live meter config, so what the dial reads is
 *   what the hardware would command. That is the point: this is the tool for
 *   deciding the dial-face artwork.
 */

const SVG_NS = "http://www.w3.org/2000/svg";

function el(name, attrs = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  return node;
}

function polar(cx, cy, radius, degrees) {
  const rad = ((degrees - 90) * Math.PI) / 180;
  return [cx + radius * Math.cos(rad), cy + radius * Math.sin(rad)];
}

function arcPath(cx, cy, radius, fromDeg, toDeg) {
  const [x0, y0] = polar(cx, cy, radius, fromDeg);
  const [x1, y1] = polar(cx, cy, radius, toDeg);
  const large = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
  const sweep = toDeg > fromDeg ? 1 : 0;
  return `M ${x0} ${y0} A ${radius} ${radius} 0 ${large} ${sweep} ${x1} ${y1}`;
}

/** Format a scale number without trailing noise. */
function scaleLabel(value) {
  const abs = Math.abs(value);
  const decimals = abs >= 100 ? 0 : abs >= 10 ? 1 : 2;
  return value.toFixed(decimals).replace(/\.?0+$/, (m) =>
    m.includes(".") ? "" : m
  );
}

/**
 * Build one dial as an SVG group, in panel inches.
 *
 * Returns { group, setDeflection } — the caller animates by calling
 * setDeflection with a value already eased and calibrated by the shared maths.
 */
export function createDial({
  cx,
  cy,
  bezelOd,
  label,
  unit,
  centre,
  span,
  sweepDegrees = 90,
  centreBandFraction = 0.25,
  showBands = true,
}) {
  const r = bezelOd / 2;
  const group = el("g", { class: "dial" });

  // Pivot sits low in the case and the arc sweeps above it — what makes a
  // panel meter read as a panel meter rather than as a car speedometer.
  // Screen space, so "low" is a larger y.
  const pivotY = cy + r * 0.58;
  const scaleR = r * 0.92;
  const half = sweepDegrees / 2;

  // Bezel: engraved ring on clear stock, not a bevelled chrome donut.
  group.appendChild(
    el("circle", {
      cx,
      cy,
      r,
      fill: "var(--panel-tint)",
      stroke: "var(--engrave)",
      "stroke-width": 0.02,
    })
  );
  group.appendChild(
    el("circle", {
      cx,
      cy,
      r: r - 0.09,
      fill: "none",
      stroke: "var(--rule)",
      "stroke-width": 0.012,
    })
  );

  // Three bands: below target, on target, above target — the dividers the
  // fabrication notes call for, engraved from the back.
  if (showBands) {
    const bandInner = scaleR - 0.13;
    const bandOuter = scaleR + 0.055;
    const centreHalf = half * centreBandFraction;
    const bands = [
      [-half, -centreHalf],
      [-centreHalf, centreHalf],
      [centreHalf, half],
    ];
    bands.forEach(([from, to], i) => {
      const [ix0, iy0] = polar(cx, pivotY, bandInner, from);
      const [ox0, oy0] = polar(cx, pivotY, bandOuter, from);
      const [ox1, oy1] = polar(cx, pivotY, bandOuter, to);
      const [ix1, iy1] = polar(cx, pivotY, bandInner, to);
      const large = 0;
      group.appendChild(
        el("path", {
          d:
            `M ${ix0} ${iy0} L ${ox0} ${oy0} ` +
            `A ${bandOuter} ${bandOuter} 0 ${large} 1 ${ox1} ${oy1} ` +
            `L ${ix1} ${iy1} ` +
            `A ${bandInner} ${bandInner} 0 ${large} 0 ${ix0} ${iy0} Z`,
          fill: i === 1 ? "rgba(28,27,25,0.055)" : "rgba(28,27,25,0.015)",
          stroke: "var(--engrave)",
          "stroke-width": 0.008,
        })
      );
    });
  }

  // Scale arc.
  group.appendChild(
    el("path", {
      d: arcPath(cx, pivotY, scaleR, -half, half),
      fill: "none",
      stroke: "var(--ink)",
      "stroke-width": 0.016,
    })
  );

  // Ticks: majors at fifths of full scale, minors between. Centre tick is
  // taller and heavier, because centre is the reading that matters.
  const majors = 10;
  for (let i = 0; i <= majors; i += 1) {
    const t = i / majors; // 0..1
    const deg = -half + t * sweepDegrees;
    const isCentre = i === majors / 2;
    const isMajor = i % (majors / 4) === 0;
    const len = isCentre ? 0.155 : isMajor ? 0.115 : 0.06;
    const [x0, y0] = polar(cx, pivotY, scaleR, deg);
    const [x1, y1] = polar(cx, pivotY, scaleR - len, deg);
    group.appendChild(
      el("line", {
        x1: x0,
        y1: y0,
        x2: x1,
        y2: y1,
        stroke: "var(--ink)",
        "stroke-width": isCentre ? 0.028 : isMajor ? 0.018 : 0.01,
      })
    );

    if (isMajor) {
      const deflection = -1 + 2 * t;
      const value = centre + deflection * span;
      const [lx, ly] = polar(cx, pivotY, scaleR - len - 0.14, deg);
      const text = el("text", {
        x: lx,
        y: ly,
        "text-anchor": "middle",
        "dominant-baseline": "middle",
        "font-size": 0.14,
        "font-family": "var(--mono)",
        fill: "var(--ink)",
      });
      text.textContent = scaleLabel(value);
      group.appendChild(text);
    }
  }

  // Legend: what it measures, and in what. Above the arc, because the pivot
  // takes the space below it.
  const nameText = el("text", {
    x: cx,
    y: cy - r * 0.62,
    "text-anchor": "middle",
    "font-size": 0.19,
    "font-family": "var(--mono)",
    "letter-spacing": 0.05,
    fill: "var(--ink)",
  });
  nameText.textContent = label;
  group.appendChild(nameText);

  if (unit) {
    const unitText = el("text", {
      x: cx,
      y: cy - r * 0.62 + 0.18,
      "text-anchor": "middle",
      "font-size": 0.11,
      "font-family": "var(--mono)",
      fill: "var(--ink-soft)",
    });
    unitText.textContent = unit;
    group.appendChild(unitText);
  }

  // Needle. Drawn straight up from the pivot and rotated, so the transform is
  // the deflection and nothing else has to move.
  const needleLength = scaleR + 0.03;
  const needle = el("g");
  needle.appendChild(
    el("line", {
      x1: cx,
      y1: pivotY,
      x2: cx,
      y2: pivotY - needleLength,
      stroke: "var(--ink)",
      "stroke-width": 0.026,
      "stroke-linecap": "round",
    })
  );
  // Counterweight tail, as on the real movement.
  needle.appendChild(
    el("line", {
      x1: cx,
      y1: pivotY,
      x2: cx,
      y2: pivotY + 0.16,
      stroke: "var(--ink)",
      "stroke-width": 0.05,
      "stroke-linecap": "round",
    })
  );
  group.appendChild(needle);
  group.appendChild(
    el("circle", { cx, cy: pivotY, r: 0.075, fill: "var(--ink)" })
  );

  function setDeflection(x) {
    const clamped = Math.max(-1, Math.min(1, x));
    const deg = clamped * half;
    needle.setAttribute("transform", `rotate(${deg} ${cx} ${pivotY})`);
  }

  setDeflection(0);
  return { group, setDeflection };
}
