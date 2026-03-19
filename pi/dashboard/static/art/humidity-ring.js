/**
 * Humidity Breathing Ring — AIR subsystem humidity visualization (v2)
 *
 * A concentric ring outside the temperature ring that "breathes":
 * radius = humidity %, opacity pulses slowly in and out.
 * Color: bright teal-cyan (0,200,220), complementing warm temperature ring.
 *
 * Hover: glowing dot + radial guide line; value shown in center disc
 * via the ring's setCenterOverride API.
 *
 * Design doc: "humidity as breathing waveforms"
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

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

    // Bright teal-cyan — saturated, distinct from temperature palette
    var HUM_COLOR = { r: 0, g: 200, b: 220 };

    function humColorRGBA(alpha) {
        return "rgba(" + HUM_COLOR.r + "," + HUM_COLOR.g + "," + HUM_COLOR.b + "," + alpha + ")";
    }

    function createHumidityRing(ctx, getCx, getCy, getMaxRadius, getHoverAngle, getMouseDist) {
        var data = null;
        var segments = [];
        var animTime = 0;
        var hoverHum = null;
        var gapThresholdMs = 20 * 60 * 1000;

        var radiusScale = d3.scaleLinear().domain([0, 100]);

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
                    hum: d.value,
                    time: date,
                };
            });

            parsed.sort(function (a, b) { return a.time - b.time; });
            parsed = padToWindow(parsed, 24 * 60 * 60 * 1000, "hum");
            data = parsed;
            recalcRadii();
        }

        function recalcRadii() {
            if (!data) return;
            var maxR = getMaxRadius();
            radiusScale.range([maxR * 0.82, maxR * 1.12]);
            gapThresholdMs = Math.max((getMedianGapMs(data) || 0) * 3, 20 * 60 * 1000);
            segments = buildSegments(data, gapThresholdMs);

            segments.forEach(function (segment) {
                var rawRadii = segment.map(function (d) { return radiusScale(d.hum); });
                var smoothed = smoothArray(rawRadii, 7);
                for (var i = 0; i < segment.length; i++) {
                    segment[i].radius = smoothed[i];
                    segment[i].angle = segment[i].renderAngle;
                }
            });
        }

        function setLiveValue(hum) {
            // not used yet but available for WebSocket updates
        }

        function render(dt) {
            if (!data || data.length < 2) return;

            animTime += dt;
            recalcRadii();

            var cx = getCx();
            var cy = getCy();
            var maxR = getMaxRadius();
            var ringMin = maxR * 0.82;

            // Breathing — strong, visible
            var breathe = 0.20 + 0.12 * Math.sin(animTime / 2500);
            var glowBreathe = 0.12 + 0.08 * Math.sin(animTime / 2500 + 0.5);

            // Check hover
            hoverHum = null;
            var hoverAngle = getHoverAngle ? getHoverAngle() : null;
            var mouseDist = getMouseDist ? getMouseDist() : Infinity;
            var hoverIdx = -1;

            if (hoverAngle !== null && mouseDist > maxR * 0.88 && mouseDist < maxR * 1.2) {
                var mNorm = normAngle(hoverAngle);
                var bestDist = Infinity;
                for (var i = 0; i < data.length; i++) {
                    var dNorm = normAngle(data[i].clockAngle);
                    var diff = Math.abs(dNorm - mNorm);
                    if (diff > Math.PI) diff = Math.PI * 2 - diff;
                    if (diff < bestDist) { bestDist = diff; hoverIdx = i; }
                }
                if (bestDist < 0.05 && hoverIdx >= 0) {
                    hoverHum = data[hoverIdx];
                }
            }

            ctx.save();
            ctx.translate(cx, cy);

            // Small angular overlap to prevent sub-pixel gaps between wedges
            var overlap = 0.003;

            // Filled area — radial gradient per wedge for depth
            segments.forEach(function (segment) {
                for (var i = 0; i < segment.length - 1; i++) {
                    var d0 = segment[i];
                    var d1 = segment[i + 1];
                    var gapMs = d1.time.getTime() - d0.time.getTime();
                    if (gapMs > gapThresholdMs) continue;

                    var r0 = d0.radius;
                    var r1 = d1.radius;

                    ctx.beginPath();
                    ctx.arc(0, 0, ringMin, d0.renderAngle, d1.renderAngle + overlap);
                    ctx.lineTo(Math.cos(d1.renderAngle) * r1, Math.sin(d1.renderAngle) * r1);
                    var midAngle = (d0.renderAngle + d1.renderAngle) / 2;
                    var midR = (r0 + r1) / 2;
                    ctx.quadraticCurveTo(
                        Math.cos(midAngle) * midR * 1.01,
                        Math.sin(midAngle) * midR * 1.01,
                        Math.cos(d0.renderAngle) * r0,
                        Math.sin(d0.renderAngle) * r0
                    );
                    ctx.closePath();

                    var grad = ctx.createRadialGradient(0, 0, ringMin, 0, 0, midR);
                    grad.addColorStop(0, humColorRGBA(breathe * 0.4));
                    grad.addColorStop(1, humColorRGBA(breathe * 1.2));
                    ctx.fillStyle = grad;
                    ctx.fill();
                }
            });

            segments.forEach(function (segment) {
                if (segment.length < 2) return;

                var points = segment.map(function (point) {
                    return {
                        x: Math.cos(point.renderAngle) * point.radius,
                        y: Math.sin(point.renderAngle) * point.radius,
                    };
                });

                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
                }
                ctx.strokeStyle = humColorRGBA(glowBreathe);
                ctx.lineWidth = 6;
                ctx.stroke();

                // Main line — organic, not mechanical
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
                }
                ctx.strokeStyle = humColorRGBA(0.3 + breathe * 0.5);
                ctx.lineWidth = 1;
                ctx.stroke();
            });

            // Hover highlight — dot + radial guide (info goes to center disc)
            if (hoverHum && hoverIdx >= 0) {
                var hr = hoverHum.radius;
                var hx = Math.cos(hoverHum.clockAngle) * hr;
                var hy = Math.sin(hoverHum.clockAngle) * hr;

                ctx.beginPath();
                ctx.arc(hx, hy, 14, 0, Math.PI * 2);
                ctx.fillStyle = humColorRGBA(0.2);
                ctx.fill();

                ctx.beginPath();
                ctx.arc(hx, hy, 5, 0, Math.PI * 2);
                ctx.fillStyle = humColorRGBA(0.8);
                ctx.fill();

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(hx, hy);
                ctx.strokeStyle = humColorRGBA(0.12);
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
            getHoverHum: function () { return hoverHum; },
        };
    }

    window.GrowLab.ArtMode.createHumidityRing = createHumidityRing;

})();
