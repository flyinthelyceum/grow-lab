/**
 * Instrument head emulator — /panel
 *
 * A digital twin of the mast's acrylic face, for judging a layout and the
 * needle encoding before anything is cut or mounted.
 *
 * The needles run on the same maths as the hardware (meter-math.js, held in
 * step with pi/services/meters.py by tests/unit/test_panel_math_parity.py) and
 * the same [meters] config, fetched from the server. So what you see here is
 * what the movements would do, not an impression of it.
 *
 * Three sources, in increasing order of how much they can be trusted:
 *   synthetic  — generators; shows failure modes that have not happened yet
 *   live       — the bench system now
 *   scrub      — real history, replayed; the honest legibility test, because
 *                invented drift can be made to look however you like
 */

import { createDial } from "./dial.js";
import { createInky } from "./inky.js";
import { applyCalibration, differentialCodes, easeAlpha, normalise } from "./meter-math.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const METERS = ["ph", "ec"];
const FRAME_HZ = 60; // screen refresh; the easing time constant governs feel
const HISTORY_POINTS = 96;
const HISTORY_INTERVAL_S = 1.0;

const state = {
  geometry: null,
  layoutId: "schedule",
  source: "synthetic",
  synthetic: "drift",
  sweepDegrees: 90,
  centreBandFraction: 0.25,
  showBands: true,
  showDimensions: false,
  overrides: {}, // meter -> { centre, span }
  replay: null,
  replayIndex: 0,
  replayPlaying: false,
  dials: {},
  inky: null,
  needles: {},
  history: { ph: [], ec: [] },
  clock: 0,
  lastFrame: null,
  lastHistorySample: 0,
};

const $ = (id) => document.getElementById(id);

function svgEl(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, String(v));
  }
  if (text !== undefined) node.textContent = text;
  return node;
}

function channel(meter) {
  const base = state.geometry.meters.channels[meter];
  const override = state.overrides[meter] || {};
  return {
    ...base,
    centre: override.centre !== undefined ? override.centre : base.centre,
    span: override.span !== undefined ? override.span : base.span,
  };
}

function currentLayout() {
  return state.geometry.layouts.find((l) => l.id === state.layoutId);
}

function unitFor(meter) {
  const cc = channel(meter);
  if (meter === "ph") return "pH";
  return cc.scale === 0.001 ? "mS/cm" : "uS/cm";
}

/* -- rendering the face -------------------------------------------------- */

function renderPanel() {
  const svg = $("panel-svg");
  const { face } = state.geometry;
  const layout = currentLayout();
  const pad = 0.28;

  svg.setAttribute(
    "viewBox",
    `${-pad} ${-pad} ${face.width + pad * 2} ${face.height + pad * 2}`
  );
  svg.replaceChildren();

  // The drawings use y-up from the bottom-left; SVG is y-down. Convert once,
  // here, rather than flipping a group — a flipped group mirrors every arc,
  // tick and glyph inside it and needs unpicking element by element.
  const sy = (panelY) => face.height - panelY;

  const root = svgEl("g");
  svg.appendChild(root);

  // The face itself: clear cast acrylic, so a tint rather than a colour.
  root.appendChild(
    svgEl("rect", {
      x: 0,
      y: 0,
      width: face.width,
      height: face.height,
      rx: 0.06,
      fill: "var(--panel-tint)",
      stroke: "var(--engrave)",
      "stroke-width": 0.03,
    })
  );

  const inset = state.geometry.corner_screw_inset;
  [
    [inset, sy(inset)],
    [face.width - inset, sy(inset)],
    [inset, sy(face.height - inset)],
    [face.width - inset, sy(face.height - inset)],
  ].forEach(([cx, cy]) => {
    root.appendChild(
      svgEl("circle", {
        cx,
        cy,
        r: 0.0675,
        fill: "none",
        stroke: "var(--ink-faint)",
        "stroke-width": 0.014,
      })
    );
  });

  state.dials = {};
  state.inky = null;

  for (const element of layout.elements) {
    if (element.kind === "dial") {
      const meter = element.id === "dial_ph" ? "ph" : "ec";
      const cc = channel(meter);
      const dial = createDial({
        cx: element.x,
        cy: sy(element.y),
        bezelOd: element.width,
        label: element.label,
        unit: unitFor(meter),
        centre: cc.centre,
        span: cc.span,
        sweepDegrees: state.sweepDegrees,
        centreBandFraction: state.centreBandFraction,
        showBands: state.showBands,
      });
      root.appendChild(dial.group);
      state.dials[meter] = dial;
    } else if (element.kind === "window") {
      const inky = createInky({ ...element, y: sy(element.y) });
      root.appendChild(inky.group);
      state.inky = inky;
    } else if (element.kind === "jewel") {
      root.appendChild(
        svgEl("circle", {
          cx: element.x,
          cy: sy(element.y),
          r: element.width / 2,
          fill: "var(--jewel)",
          "fill-opacity": 0.82,
          stroke: "var(--brass)",
          "stroke-width": 0.035,
        })
      );
    } else if (element.kind === "amber") {
      root.appendChild(
        svgEl("circle", {
          cx: element.x,
          cy: sy(element.y),
          r: element.width / 2,
          id: "amber-lamp",
          fill: "var(--amber)",
          "fill-opacity": 0.18,
          stroke: "var(--brass)",
          "stroke-width": 0.022,
        })
      );
    } else if (element.kind === "knob") {
      // Bushing is 0.375; the knob body a viewer sees is larger.
      root.appendChild(
        svgEl("circle", {
          cx: element.x,
          cy: sy(element.y),
          r: 0.31,
          fill: "none",
          stroke: "var(--ink-soft)",
          "stroke-width": 0.022,
        })
      );
      root.appendChild(
        svgEl("line", {
          x1: element.x,
          y1: sy(element.y),
          x2: element.x,
          y2: sy(element.y) - 0.31,
          stroke: "var(--ink-soft)",
          "stroke-width": 0.022,
        })
      );
    }
  }

  if (state.showDimensions) renderDimensions(root, layout, face, sy);

  const collisions = layout.collisions.length || layout.out_of_bounds.length;
  $("stage-caption").textContent = collisions
    ? `${layout.name} — GEOMETRY CONFLICT`
    : `${layout.name} — ${face.width.toFixed(2)} × ${face.height.toFixed(2)} in`;
}

function renderDimensions(root, layout, face, sy) {
  const marks = svgEl("g", { "stroke-width": 0.008, stroke: "var(--flag)" });
  for (const element of layout.elements) {
    marks.appendChild(
      svgEl("line", {
        x1: 0,
        y1: sy(element.y),
        x2: face.width,
        y2: sy(element.y),
        "stroke-dasharray": "0.05 0.05",
        "stroke-opacity": 0.5,
      })
    );
    marks.appendChild(
      svgEl("line", {
        x1: element.x,
        y1: 0,
        x2: element.x,
        y2: face.height,
        "stroke-dasharray": "0.05 0.05",
        "stroke-opacity": 0.5,
      })
    );
    const t = svgEl(
      "text",
      {
        x: element.x + 0.07,
        y: sy(element.y) - 0.07,
        "font-size": 0.1,
        "font-family": "var(--mono)",
        fill: "var(--flag)",
        stroke: "none",
      },
      `${element.x.toFixed(3)}, ${element.y.toFixed(3)}`
    );
    marks.appendChild(t);
  }
  root.appendChild(marks);
}

/* -- data sources -------------------------------------------------------- */

function syntheticValues(meter, t) {
  const cc = channel(meter);
  const phaseShift = meter === "ec" ? 1.7 : 0.0;
  switch (state.synthetic) {
    case "drift":
      // Slow one-way walk out of the target band and back.
      return cc.centre + cc.span * 1.4 * Math.sin((t + phaseShift) / 40);
    case "step":
      // Square steps, to see the easing settle.
      return (
        cc.centre +
        cc.span * 0.8 * (Math.floor((t + phaseShift) / 12) % 2 === 0 ? 1 : -1)
      );
    case "noise":
      // Small target-band jitter: does the needle read as calm or as busy?
      return cc.centre + cc.span * 0.22 * (Math.random() * 2 - 1);
    case "pegged":
      // Both ends held, to check nothing overruns the scale.
      return cc.centre + cc.span * (Math.floor(t / 8) % 2 === 0 ? 3 : -3);
    case "dropout":
      // Sensor gone: 6 seconds of data, 10 of silence.
      return (t + phaseShift) % 16 < 6
        ? cc.centre + cc.span * 0.5
        : null;
    default:
      return cc.centre;
  }
}

async function fetchLive() {
  const response = await fetch("/api/meters/status");
  if (!response.ok) return null;
  const data = await response.json();
  const out = {};
  for (const meter of METERS) {
    const entry = data.meters[meter];
    out[meter] = entry && !entry.faulted ? entry.value : null;
  }
  return out;
}

async function loadReplay(window) {
  const response = await fetch(`/api/panel/replay?window=${window}`);
  if (!response.ok) return;
  state.replay = await response.json();
  state.replayIndex = 0;
  const scrub = $("scrub");
  scrub.max = Math.max(0, state.replay.count - 1);
  scrub.value = 0;
  $("replay-count").textContent = state.replay.count
    ? `${state.replay.count} frames`
    : "no data in window";
  updateScrubLabel();
}

function updateScrubLabel() {
  if (!state.replay || !state.replay.count) {
    $("scrub-at").textContent = "—";
    return;
  }
  const frame = state.replay.frames[state.replayIndex];
  $("scrub-at").textContent = new Date(frame.t).toLocaleString();
}

function replayValues() {
  if (!state.replay || !state.replay.count) return { ph: null, ec: null };
  const frame = state.replay.frames[state.replayIndex];
  return { ph: frame.ph, ec: frame.ec };
}

/* -- the loop ------------------------------------------------------------ */

function needle(meter) {
  if (!state.needles[meter]) {
    state.needles[meter] = { displayed: 0, target: 0, faulted: true, value: null };
  }
  return state.needles[meter];
}

function setTargets(values) {
  for (const meter of METERS) {
    const n = needle(meter);
    const raw = values[meter];
    const cc = channel(meter);
    if (raw === null || raw === undefined) {
      // Same rule as the service: a missing reading eases the needle home
      // and raises a flag rather than freezing or slamming it.
      n.target = 0;
      n.faulted = true;
      n.value = null;
    } else {
      const scaled = raw * cc.scale;
      n.target = normalise(scaled, cc.centre, cc.span);
      n.faulted = false;
      n.value = scaled;
    }
  }
}

function frame(now) {
  const dt = state.lastFrame === null ? 1 / FRAME_HZ : (now - state.lastFrame) / 1000;
  state.lastFrame = now;
  state.clock += dt;

  if (state.source === "synthetic") {
    setTargets({
      ph: syntheticValues("ph", state.clock),
      ec: syntheticValues("ec", state.clock),
    });
  } else if (state.source === "scrub") {
    if (state.replayPlaying && state.replay && state.replay.count) {
      state.replayIndex = (state.replayIndex + 1) % state.replay.count;
      $("scrub").value = state.replayIndex;
      updateScrubLabel();
    }
    setTargets(replayValues());
  }

  const alpha = easeAlpha(dt, state.geometry.meters.time_constant_seconds);

  for (const meter of METERS) {
    const n = needle(meter);
    n.displayed += (n.target - n.displayed) * alpha;

    const cc = channel(meter);
    let commanded = applyCalibration(
      n.displayed,
      (cc.calibration || []).map((p) => [p[0], p[1]])
    );
    if (cc.invert) commanded = -commanded;

    const dial = state.dials[meter];
    if (dial) dial.setDeflection(commanded);

    const [pos, neg] = differentialCodes(commanded);
    paintReadout(meter, n, commanded, pos, neg);

  }

  // The e-ink waveform is the *rhythm*, so sample it on a clock rather than
  // per frame: 96 points at 1 Hz is a minute and a half of movement. Sampling
  // every frame gave 96 points at 60 Hz — 1.6 seconds, which reads as a flat
  // line no matter what the needles are doing.
  if (state.clock - state.lastHistorySample >= HISTORY_INTERVAL_S) {
    state.lastHistorySample = state.clock;
    for (const meter of METERS) {
      const hist = state.history[meter];
      hist.push(needle(meter).displayed);
      if (hist.length > HISTORY_POINTS) hist.shift();
    }
  }

  paintInky();
  requestAnimationFrame(frame);
}

function paintReadout(meter, n, commanded, pos, neg) {
  const row = $(`row-${meter}`);
  if (!row) return;
  row.classList.toggle("faulted", n.faulted);
  $(`val-${meter}`).textContent =
    n.value === null ? "—" : n.value.toFixed(meter === "ph" ? 2 : 3);
  $(`def-${meter}`).textContent = `${commanded >= 0 ? "+" : ""}${commanded.toFixed(3)}`;
  $(`dac-${meter}`).textContent = `${pos} / ${neg}`;
  $(`state-${meter}`).textContent = n.faulted ? "STALE" : "tracking";
}

function paintInky() {
  if (!state.inky) return;
  const phNeedle = needle("ph");
  const anyFault = METERS.some((m) => needle(m).faulted);
  const amber = document.getElementById("amber-lamp");
  if (amber) {
    // Tend-me: lit when either channel is out of its target band or stale.
    const outOfBand = METERS.some((m) => Math.abs(needle(m).displayed) > 0.5);
    amber.setAttribute("fill-opacity", outOfBand || anyFault ? 0.92 : 0.18);
  }

  state.inky.update({
    series: state.history.ph.length ? state.history.ph : [0],
    phase: state.source === "scrub" ? "REPLAY" : "VIGIL",
    ambient: anyFault ? "--°" : "72°",
    tended: "tended 6h ago",
    next: phNeedle.faulted ? "sensor stale" : "next 04:00",
  });
}

/* -- controls ------------------------------------------------------------ */

function buildLayoutButtons() {
  const host = $("layout-seg");
  host.replaceChildren();
  for (const layout of state.geometry.layouts) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = layout.is_schedule ? `${layout.name} ✓` : layout.name;
    button.setAttribute("aria-pressed", String(layout.id === state.layoutId));
    button.addEventListener("click", () => {
      state.layoutId = layout.id;
      buildLayoutButtons();
      renderPanel();
      paintRationale();
    });
    host.appendChild(button);
  }
}

function paintRationale() {
  const layout = currentLayout();
  const host = $("rationale");
  host.replaceChildren();
  const p = document.createElement("p");
  p.className = "rationale";
  if (layout.is_schedule) {
    const em = document.createElement("em");
    em.textContent = "Current drawings. ";
    p.appendChild(em);
  }
  p.appendChild(document.createTextNode(layout.rationale));
  host.appendChild(p);
}

function bindSegment(id, key, onChange) {
  $(id).querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state[key] = button.dataset.value;
      $(id).querySelectorAll("button").forEach((b) => {
        b.setAttribute("aria-pressed", String(b === button));
      });
      if (onChange) onChange(button.dataset.value);
    });
  });
}

function bindOverride(meter, field, inputId, outputId, format) {
  const input = $(inputId);
  const output = $(outputId);
  const base = state.geometry.meters.channels[meter];
  input.value = base[field];
  output.textContent = format(base[field]);
  input.addEventListener("input", () => {
    state.overrides[meter] = state.overrides[meter] || {};
    state.overrides[meter][field] = Number(input.value);
    output.textContent = format(Number(input.value));
    renderPanel(); // scale numbers are derived from centre and span
  });
}

function bindControls() {
  buildLayoutButtons();
  paintRationale();

  bindSegment("source-seg", "source", (value) => {
    state.needles = {};
    $("scrub-controls").hidden = value !== "scrub";
    $("synthetic-seg").hidden = value !== "synthetic";
    if (value === "scrub" && !state.replay) loadReplay($("replay-window").value);
    if (value === "live") pollLive();
  });
  bindSegment("synthetic-seg", "synthetic");

  $("sweep").addEventListener("input", (e) => {
    state.sweepDegrees = Number(e.target.value);
    $("sweep-out").textContent = `${state.sweepDegrees}°`;
    renderPanel();
  });
  $("band").addEventListener("input", (e) => {
    state.centreBandFraction = Number(e.target.value);
    $("band-out").textContent = `${Math.round(state.centreBandFraction * 100)}%`;
    renderPanel();
  });
  $("show-bands").addEventListener("change", (e) => {
    state.showBands = e.target.checked;
    renderPanel();
  });
  $("show-dims").addEventListener("change", (e) => {
    state.showDimensions = e.target.checked;
    renderPanel();
  });

  bindOverride("ph", "centre", "ph-centre", "ph-centre-out", (v) => v.toFixed(2));
  bindOverride("ph", "span", "ph-span", "ph-span-out", (v) => `±${v.toFixed(2)}`);
  bindOverride("ec", "centre", "ec-centre", "ec-centre-out", (v) => v.toFixed(2));
  bindOverride("ec", "span", "ec-span", "ec-span-out", (v) => `±${v.toFixed(2)}`);

  $("scrub").addEventListener("input", (e) => {
    state.replayIndex = Number(e.target.value);
    state.replayPlaying = false;
    $("replay-play").setAttribute("aria-pressed", "false");
    updateScrubLabel();
  });
  $("replay-play").addEventListener("click", () => {
    state.replayPlaying = !state.replayPlaying;
    $("replay-play").setAttribute("aria-pressed", String(state.replayPlaying));
  });
  $("replay-window").addEventListener("change", (e) => loadReplay(e.target.value));
  $("print").addEventListener("click", () => window.print());
}

async function pollLive() {
  if (state.source !== "live") return;
  const values = await fetchLive();
  if (values) setTargets(values);
  // Sensors update on the order of minutes; the needle eases between.
  setTimeout(pollLive, 3000);
}

function paintNotes() {
  const host = $("notes");
  host.replaceChildren();
  for (const note of state.geometry.notes) {
    const li = document.createElement("li");
    li.textContent = note;
    host.appendChild(li);
  }
  if (state.geometry.dial.cut_pending_calipers) {
    const li = document.createElement("li");
    const flag = document.createElement("span");
    flag.className = "flag";
    flag.textContent = "provisional";
    li.appendChild(flag);
    li.appendChild(
      document.createTextNode(
        " Needle sweep angle is not a measured figure either — 90° is typical " +
          "for the size class. It changes legibility, so it is a control rather " +
          "than a constant."
      )
    );
    host.appendChild(li);
  }
}

async function main() {
  const response = await fetch("/api/panel/geometry");
  state.geometry = await response.json();
  bindControls();
  renderPanel();
  paintNotes();
  requestAnimationFrame(frame);
}

main();
