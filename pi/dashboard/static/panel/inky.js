/**
 * Inky Impression 7.3 in render for the panel emulator.
 *
 * 800 x 480 into a 6.30 x 3.78 in window. Content follows
 * UI_UX_DESIGN_REFERENCE.md section 5: slow and unlabeled — a temporal
 * waveform, the current phase, last-tended and next event, ambient degrees F.
 *
 * Drawn in the e-paper's own register: reflective off-white ground, no
 * emissive colour, a restricted ink set. It is here so a layout is judged as
 * dials-plus-screen together, which is how the face will actually be seen.
 */

const SVG_NS = "http://www.w3.org/2000/svg";
const PX_W = 800;
const PX_H = 480;

function el(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  if (text !== undefined) node.textContent = text;
  return node;
}

/** Catmull-Rom through the points, so the waveform reads as a rhythm. */
function smoothPath(points) {
  if (points.length < 2) return "";
  let d = `M ${points[0][0]} ${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i === 0 ? 0 : i - 1];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2 > points.length - 1 ? points.length - 1 : i + 2];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += ` C ${c1x} ${c1y}, ${c2x} ${c2y}, ${p2[0]} ${p2[1]}`;
  }
  return d;
}

/**
 * Build the screen as an SVG group scaled into the panel window.
 * Returns { group, update }.
 */
export function createInky({ x, y, width, height }) {
  const group = el("g", { class: "inky" });

  // Window aperture in screen inches; contents drawn in pixels and scaled.
  const left = x - width / 2;
  const top = y - height / 2;
  group.appendChild(
    el("rect", {
      x: left,
      y: top,
      width,
      height,
      fill: "#f7f6f2",
      stroke: "var(--engrave)",
      "stroke-width": 0.02,
    })
  );

  const inner = el("g", {
    transform: `translate(${left} ${top}) scale(${width / PX_W} ${height / PX_H})`,
  });
  group.appendChild(inner);

  const wave = el("path", {
    fill: "none",
    stroke: "#26251f",
    "stroke-width": 3,
    "stroke-linecap": "round",
  });
  const waveBaseline = el("line", {
    x1: 60,
    y1: 250,
    x2: PX_W - 60,
    y2: 250,
    stroke: "#c4c0b6",
    "stroke-width": 1.5,
    "stroke-dasharray": "6 8",
  });

  const phase = el("text", {
    x: 60,
    y: 92,
    "font-size": 54,
    "font-family": "var(--mono)",
    "letter-spacing": 6,
    fill: "#26251f",
  });
  const ambient = el("text", {
    x: PX_W - 60,
    y: 92,
    "text-anchor": "end",
    "font-size": 54,
    "font-family": "var(--mono)",
    fill: "#26251f",
  });
  const tended = el("text", {
    x: 60,
    y: PX_H - 54,
    "font-size": 26,
    "font-family": "var(--mono)",
    "letter-spacing": 2,
    fill: "#6b6862",
  });
  const next = el("text", {
    x: PX_W - 60,
    y: PX_H - 54,
    "text-anchor": "end",
    "font-size": 26,
    "font-family": "var(--mono)",
    "letter-spacing": 2,
    fill: "#6b6862",
  });

  inner.appendChild(waveBaseline);
  inner.appendChild(wave);
  [phase, ambient, tended, next].forEach((t) => inner.appendChild(t));

  /**
   * @param {object} state
   * @param {number[]} state.series values in -1..1, oldest first
   * @param {string} state.phase
   * @param {string} state.ambient
   * @param {string} state.tended
   * @param {string} state.next
   */
  function update(state) {
    const series = state.series && state.series.length ? state.series : [0];
    const x0 = 60;
    const x1 = PX_W - 60;
    const midY = 250;
    const amplitude = 120;
    const points = series.map((v, i) => {
      const t = series.length === 1 ? 0.5 : i / (series.length - 1);
      const clamped = Math.max(-1, Math.min(1, v));
      return [x0 + t * (x1 - x0), midY + clamped * amplitude];
    });
    wave.setAttribute("d", smoothPath(points));

    phase.textContent = state.phase || "";
    ambient.textContent = state.ambient || "";
    tended.textContent = state.tended || "";
    next.textContent = state.next || "";
  }

  update({ series: [0], phase: "", ambient: "", tended: "", next: "" });
  return { group, update };
}
