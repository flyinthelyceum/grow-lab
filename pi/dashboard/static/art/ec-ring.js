/**
 * EC Ring — RESERVOIR subsystem electrical conductivity visualization
 *
 * A concentric ring inside the pH ring showing 24h reservoir EC.
 * Color: gold-to-electric-blue gradient mapped to EC value (µS/cm).
 * Animation: sparkle points along the outer edge suggest dissolved mineral
 * conductivity — 10 points with oscillating alpha.
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

    // --- EC ring constants ---

    var EC_MIN = 0;
    var EC_MAX = 3000;
    var EC_IDEAL_MIN = 800;
    var EC_IDEAL_MAX = 1800;
    var SPARKLE_COUNT = 10;

    // Ring band relative to minR (inner edge of temperature ring)
    var BAND_INNER = 0.45;
    var BAND_OUTER = 0.65;

    function createEcRing(ctx, getCx, getCy, getMaxR, getMinR, getHoverAngle, getMouseDist) {
        var data = null;
        var segments = [];
        var animTime = 0;
        var hoverEc = null;
        var hoverDistance = Infinity;
        var liveValue = null;
        var gapThresholdMs = 20 * 60 * 1000;

        var radiusScale = d3.scaleLinear().domain([EC_MIN, EC_MAX]);

        // Pre-compute sparkle phase offsets
        var sparkles = [];
        for (var s = 0; s < SPARKLE_COUNT; s++) {
            sparkles.push({
                angle: (s / SPARKLE_COUNT) * Math.PI * 2 - Math.PI / 2,
                phase: Math.random() * Math.PI * 2,
            });
        }

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
                    ec: d.value,
                    time: date,
                };
            });

            parsed.sort(function (a, b) { return a.time - b.time; });
            parsed = padToWindow(parsed, 24 * 60 * 60 * 1000, "ec");
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
                var rawRadii = segment.map(function (d) { return radiusScale(d.ec); });
                var smoothed = smoothArray(rawRadii, 7);
                for (var i = 0; i < segment.length; i++) {
                    segment[i].radius = smoothed[i];
                    segment[i].angle = segment[i].renderAngle;
                }
            });
        }

        function setLiveValue(ec) {
            liveValue = ec;
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
            var baseAlpha = 0.22;

            // Check hover
            hoverEc = null;
            hoverDistance = Infinity;
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
                    var candidate = data[hoverIdx];
                    var radialDistance = Math.abs(mouseDist - candidate.radius);
                    var hoverThreshold = Math.max(12, (outerR - innerR) * 0.6);
                    if (radialDistance <= hoverThreshold) {
                        hoverEc = candidate;
                        hoverDistance = radialDistance;
                    }
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
                    var avgEc = (d0.ec + d1.ec) / 2;

                    ctx.beginPath();
                    ctx.arc(0, 0, innerR, d0.renderAngle, d1.renderAngle + overlap);
                    ctx.lineTo(
                        Math.cos(d1.renderAngle) * r1,
                        Math.sin(d1.renderAngle) * r1
                    );
                    var midAngle = (d0.renderAngle + d1.renderAngle) / 2;
                    var midR = (r0 + r1) / 2;
                    ctx.quadraticCurveTo(
                        Math.cos(midAngle) * midR * 1.01,
                        Math.sin(midAngle) * midR * 1.01,
                        Math.cos(d0.renderAngle) * r0,
                        Math.sin(d0.renderAngle) * r0
                    );
                    ctx.closePath();

                    var grad = ctx.createRadialGradient(0, 0, innerR, 0, 0, midR);
                    grad.addColorStop(0, Art.ecColorRGBA(avgEc, baseAlpha * 0.3));
                    grad.addColorStop(1, Art.ecColorRGBA(avgEc, baseAlpha));
                    ctx.fillStyle = grad;
                    ctx.fill();
                }
            });

            // Outer edge stroke — smooth quadratic curves
            segments.forEach(function (segment) {
                if (segment.length < 2) return;

                var points = segment.map(function (point) {
                    return {
                        x: Math.cos(point.renderAngle) * point.radius,
                        y: Math.sin(point.renderAngle) * point.radius,
                        ec: point.ec,
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
                ctx.strokeStyle = Art.ecColorRGBA(data[Math.floor(data.length / 2)].ec, 0.08);
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
                ctx.strokeStyle = Art.ecColorRGBA(data[Math.floor(data.length / 2)].ec, 0.28);
                ctx.lineWidth = 1;
                ctx.stroke();
            });

            // Ideal-zone arcs (EC 800 and 1800 µS/cm) — faint dashed reference
            ctx.setLineDash([4, 8]);
            ctx.lineWidth = 0.5;

            var idealMinR = radiusScale(EC_IDEAL_MIN);
            ctx.beginPath();
            ctx.arc(0, 0, idealMinR, 0, Math.PI * 2);
            ctx.strokeStyle = Art.ecColorRGBA(EC_IDEAL_MIN, 0.06);
            ctx.stroke();

            var idealMaxR = radiusScale(EC_IDEAL_MAX);
            ctx.beginPath();
            ctx.arc(0, 0, idealMaxR, 0, Math.PI * 2);
            ctx.strokeStyle = Art.ecColorRGBA(EC_IDEAL_MAX, 0.06);
            ctx.stroke();

            ctx.setLineDash([]);

            // Sparkle effect — tiny dots along outer edge with oscillating alpha
            var medianEc = data.length > 0 ? data[Math.floor(data.length / 2)].ec : 1000;
            for (var si = 0; si < sparkles.length; si++) {
                var sp = sparkles[si];
                var sparkleAlpha = 0.15 + 0.35 * Math.max(0, Math.sin(animTime / 400 + sp.phase));
                var sparkleR = outerR + 1;

                ctx.beginPath();
                ctx.arc(
                    Math.cos(sp.angle) * sparkleR,
                    Math.sin(sp.angle) * sparkleR,
                    1.5, 0, Math.PI * 2
                );
                ctx.fillStyle = Art.ecColorRGBA(medianEc, sparkleAlpha);
                ctx.fill();
            }

            // Hover highlight
            if (hoverEc && hoverIdx >= 0) {
                var hr = hoverEc.radius;
                var hx = Math.cos(hoverEc.clockAngle) * hr;
                var hy = Math.sin(hoverEc.clockAngle) * hr;

                ctx.beginPath();
                ctx.arc(hx, hy, 12, 0, Math.PI * 2);
                ctx.fillStyle = Art.ecColorRGBA(hoverEc.ec, 0.2);
                ctx.fill();

                ctx.beginPath();
                ctx.arc(hx, hy, 4, 0, Math.PI * 2);
                ctx.fillStyle = Art.ecColorRGBA(hoverEc.ec, 0.8);
                ctx.fill();

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(hx, hy);
                ctx.strokeStyle = Art.ecColorRGBA(hoverEc.ec, 0.12);
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
            getHoverEc: function () { return hoverEc; },
            getHoverDistance: function () { return hoverDistance; },
        };
    }

    window.GrowLab.ArtMode.createEcRing = createEcRing;

})();
