/**
 * pH Ring — RESERVOIR subsystem pH visualization
 *
 * A concentric ring inside the temperature ring showing 24h reservoir pH.
 * Color: green-to-violet litmus gradient mapped to pH value.
 * Animation: slow sinusoidal phase-shift along the ring edge ("flowing liquid").
 * Faint ideal-zone arcs at pH 5.5 and 6.5 (hydroponic sweet spot).
 *
 * Hover: glowing dot + radial guide line; value shown in center disc
 * via the ring's setCenterOverride API.
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    // --- Shared utilities (duplicated from humidity-ring; no ES6 modules) ---

    function timeToAngle(date) {
        var hours = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
        return (hours / 24) * Math.PI * 2 - Math.PI / 2;
    }

    function normAngle(a) {
        while (a > Math.PI) a -= Math.PI * 2;
        while (a < -Math.PI) a += Math.PI * 2;
        return a;
    }

    function smoothArray(arr, windowSize) {
        var half = Math.floor(windowSize / 2);
        var result = [];
        for (var i = 0; i < arr.length; i++) {
            var sum = 0, count = 0;
            for (var j = i - half; j <= i + half; j++) {
                if (j < 0 || j >= arr.length) continue;
                sum += arr[j];
                count++;
            }
            result.push(sum / count);
        }
        return result;
    }

    function getMedianGapMs(points) {
        var diffs = [];
        for (var i = 1; i < points.length; i++) {
            var diff = points[i].time.getTime() - points[i - 1].time.getTime();
            if (diff > 0) diffs.push(diff);
        }
        return diffs.length ? (d3.median(diffs) || 0) : 0;
    }

    function buildSegments(points, gapThresholdMs) {
        if (!points || points.length === 0) return [];

        var segments = [];
        var segment = [];
        var angleOffset = 0;
        var prevClockAngle = null;

        function commitSegment() {
            if (segment.length > 0) {
                segments.push(segment);
                segment = [];
            }
            angleOffset = 0;
            prevClockAngle = null;
        }

        for (var i = 0; i < points.length; i++) {
            var point = points[i];
            var prevPoint = segment.length ? segment[segment.length - 1] : null;

            if (prevPoint && (point.time.getTime() - prevPoint.time.getTime()) > gapThresholdMs) {
                commitSegment();
            }

            if (prevClockAngle !== null && point.clockAngle < prevClockAngle - Math.PI) {
                angleOffset += Math.PI * 2;
            }

            point.renderAngle = point.clockAngle + angleOffset;
            segment.push(point);
            prevClockAngle = point.clockAngle;
        }

        commitSegment();
        return segments;
    }

    function padToWindow(points, windowMs, valueKey) {
        if (!points || points.length === 0) return [];

        var endTime = new Date();
        var startTime = new Date(endTime.getTime() - windowMs);
        var padded = points.slice();
        var first = padded[0];
        var last = padded[padded.length - 1];

        if (first.time.getTime() > startTime.getTime()) {
            var firstClone = {};
            for (var key in first) firstClone[key] = first[key];
            firstClone.time = startTime;
            firstClone.clockAngle = timeToAngle(startTime);
            firstClone.angle = firstClone.clockAngle;
            firstClone.synthetic = true;
            firstClone[valueKey] = first[valueKey];
            padded.unshift(firstClone);
        }

        if (last.time.getTime() < endTime.getTime()) {
            var lastClone = {};
            for (var key2 in last) lastClone[key2] = last[key2];
            lastClone.time = endTime;
            lastClone.clockAngle = timeToAngle(endTime);
            lastClone.angle = lastClone.clockAngle;
            lastClone.synthetic = true;
            lastClone[valueKey] = last[valueKey];
            padded.push(lastClone);
        }

        return padded;
    }

    // --- pH ring constants ---

    var PH_MIN = 4.0;
    var PH_MAX = 9.0;
    var PH_IDEAL_MIN = 5.5;
    var PH_IDEAL_MAX = 6.5;

    // Ring band relative to minR (inner edge of temperature ring)
    var BAND_INNER = 0.67;
    var BAND_OUTER = 0.86;

    function createPhRing(ctx, getCx, getCy, getMaxR, getMinR, getHoverAngle, getMouseDist) {
        var data = null;
        var segments = [];
        var animTime = 0;
        var hoverPh = null;
        var liveValue = null;
        var gapThresholdMs = 20 * 60 * 1000;

        var radiusScale = d3.scaleLinear().domain([PH_MIN, PH_MAX]);

        function update(readings) {
            if (!readings || readings.length === 0) {
                data = null;
                segments = [];
                return;
            }

            var parsed = readings.map(function (d) {
                var date = new Date(d.timestamp);
                return {
                    angle: timeToAngle(date),
                    clockAngle: timeToAngle(date),
                    ph: d.value,
                    time: date,
                };
            });

            parsed.sort(function (a, b) { return a.time - b.time; });
            parsed = padToWindow(parsed, 24 * 60 * 60 * 1000, "ph");
            data = parsed;
            recalcRadii();
        }

        function recalcRadii() {
            if (!data) return;
            var minR = getMinR();
            radiusScale.range([minR * BAND_INNER, minR * BAND_OUTER]);
            gapThresholdMs = Math.max((getMedianGapMs(data) || 0) * 3, 20 * 60 * 1000);
            segments = buildSegments(data, gapThresholdMs);

            segments.forEach(function (segment) {
                var rawRadii = segment.map(function (d) { return radiusScale(d.ph); });
                var smoothed = smoothArray(rawRadii, 7);
                for (var i = 0; i < segment.length; i++) {
                    segment[i].radius = smoothed[i];
                    segment[i].angle = segment[i].renderAngle;
                }
            });
        }

        function setLiveValue(ph) {
            liveValue = ph;
        }

        function render(dt) {
            if (!data || data.length < 2) return;

            animTime += dt;
            recalcRadii();

            var cx = getCx();
            var cy = getCy();
            var minR = getMinR();
            var innerR = minR * BAND_INNER;
            var outerR = minR * BAND_OUTER;

            // Slow phase-shift oscillation — "flowing liquid" feel
            var phaseShift = animTime / 3500;
            var baseAlpha = 0.22;

            // Check hover
            hoverPh = null;
            var hoverAngle = getHoverAngle ? getHoverAngle() : null;
            var mouseDist = getMouseDist ? getMouseDist() : Infinity;
            var hoverIdx = -1;

            if (hoverAngle !== null && mouseDist > innerR * 0.9 && mouseDist < outerR * 1.1) {
                var mNorm = normAngle(hoverAngle);
                var bestDist = Infinity;
                for (var i = 0; i < data.length; i++) {
                    var dNorm = normAngle(data[i].clockAngle);
                    var diff = Math.abs(dNorm - mNorm);
                    if (diff > Math.PI) diff = Math.PI * 2 - diff;
                    if (diff < bestDist) { bestDist = diff; hoverIdx = i; }
                }
                if (bestDist < 0.05 && hoverIdx >= 0) {
                    hoverPh = data[hoverIdx];
                }
            }

            ctx.save();
            ctx.translate(cx, cy);

            var overlap = 0.003;

            // Filled wedge segments with radial gradient
            segments.forEach(function (segment) {
                for (var i = 0; i < segment.length - 1; i++) {
                    var d0 = segment[i];
                    var d1 = segment[i + 1];
                    var gapMs = d1.time.getTime() - d0.time.getTime();
                    if (gapMs > gapThresholdMs) continue;

                    var r0 = d0.radius;
                    var r1 = d1.radius;
                    var avgPh = (d0.ph + d1.ph) / 2;

                    // Phase-shift: small radial offset per point for flowing effect
                    var flow0 = Math.sin(d0.renderAngle * 3 + phaseShift) * (outerR - innerR) * 0.04;
                    var flow1 = Math.sin(d1.renderAngle * 3 + phaseShift) * (outerR - innerR) * 0.04;

                    ctx.beginPath();
                    ctx.arc(0, 0, innerR, d0.renderAngle, d1.renderAngle + overlap);
                    ctx.lineTo(
                        Math.cos(d1.renderAngle) * (r1 + flow1),
                        Math.sin(d1.renderAngle) * (r1 + flow1)
                    );
                    var midAngle = (d0.renderAngle + d1.renderAngle) / 2;
                    var midR = (r0 + r1) / 2 + (flow0 + flow1) / 2;
                    ctx.quadraticCurveTo(
                        Math.cos(midAngle) * midR * 1.01,
                        Math.sin(midAngle) * midR * 1.01,
                        Math.cos(d0.renderAngle) * (r0 + flow0),
                        Math.sin(d0.renderAngle) * (r0 + flow0)
                    );
                    ctx.closePath();

                    var grad = ctx.createRadialGradient(0, 0, innerR, 0, 0, midR);
                    grad.addColorStop(0, Art.phColorRGBA(avgPh, baseAlpha * 0.3));
                    grad.addColorStop(1, Art.phColorRGBA(avgPh, baseAlpha));
                    ctx.fillStyle = grad;
                    ctx.fill();
                }
            });

            // Outer edge stroke — smooth quadratic curves
            segments.forEach(function (segment) {
                if (segment.length < 2) return;

                var points = segment.map(function (point, idx) {
                    var flow = Math.sin(point.renderAngle * 3 + phaseShift) * (outerR - innerR) * 0.04;
                    return {
                        x: Math.cos(point.renderAngle) * (point.radius + flow),
                        y: Math.sin(point.renderAngle) * (point.radius + flow),
                        ph: point.ph,
                    };
                });

                // Glow stroke
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
                }
                ctx.strokeStyle = Art.phColorRGBA(data[Math.floor(data.length / 2)].ph, 0.08);
                ctx.lineWidth = 5;
                ctx.stroke();

                // Main line
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
                }
                ctx.strokeStyle = Art.phColorRGBA(data[Math.floor(data.length / 2)].ph, 0.28);
                ctx.lineWidth = 1;
                ctx.stroke();
            });

            // Ideal-zone arcs (pH 5.5 and 6.5) — faint dashed reference lines
            ctx.setLineDash([4, 8]);
            ctx.lineWidth = 0.5;

            var idealMinR = radiusScale(PH_IDEAL_MIN);
            ctx.beginPath();
            ctx.arc(0, 0, idealMinR, 0, Math.PI * 2);
            ctx.strokeStyle = Art.phColorRGBA(PH_IDEAL_MIN, 0.06);
            ctx.stroke();

            var idealMaxR = radiusScale(PH_IDEAL_MAX);
            ctx.beginPath();
            ctx.arc(0, 0, idealMaxR, 0, Math.PI * 2);
            ctx.strokeStyle = Art.phColorRGBA(PH_IDEAL_MAX, 0.06);
            ctx.stroke();

            ctx.setLineDash([]);

            // Hover highlight
            if (hoverPh && hoverIdx >= 0) {
                var flow = Math.sin(hoverPh.renderAngle * 3 + phaseShift) * (outerR - innerR) * 0.04;
                var hr = hoverPh.radius + flow;
                var hx = Math.cos(hoverPh.clockAngle) * hr;
                var hy = Math.sin(hoverPh.clockAngle) * hr;

                ctx.beginPath();
                ctx.arc(hx, hy, 12, 0, Math.PI * 2);
                ctx.fillStyle = Art.phColorRGBA(hoverPh.ph, 0.2);
                ctx.fill();

                ctx.beginPath();
                ctx.arc(hx, hy, 4, 0, Math.PI * 2);
                ctx.fillStyle = Art.phColorRGBA(hoverPh.ph, 0.8);
                ctx.fill();

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(hx, hy);
                ctx.strokeStyle = Art.phColorRGBA(hoverPh.ph, 0.12);
                ctx.lineWidth = 0.5;
                ctx.setLineDash([3, 5]);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            ctx.restore();
        }

        return {
            update: update,
            setLiveValue: setLiveValue,
            render: render,
            getHoverPh: function () { return hoverPh; },
        };
    }

    window.GrowLab.ArtMode.createPhRing = createPhRing;

})();
