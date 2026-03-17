/**
 * Radial Thermal Ring — AIR subsystem art visualization
 *
 * 24h temperature data rendered in polar coordinates on canvas.
 * Midnight at top (12 o'clock), noon at bottom.
 * Radius = temperature (warmer expands outward, cooler contracts).
 * Color shifts deep blue → teal → warm amber along the ring.
 *
 * Features:
 *  - Smoothed ring edge (7-point moving average + quadratic curves)
 *  - Center disc with current temperature readout
 *  - Pulsing "now" marker that tracks current time
 *  - Hover interaction: mouse over ring reveals time + temp at any point
 *  - 8 clock labels (3-hour intervals)
 *  - Breathing glow animation on outer edge
 *
 * Uses D3 for math (scales, extent), Canvas 2D for rendering.
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    // Time-of-day → angle: midnight = -PI/2 (top), clockwise
    function timeToAngle(date) {
        var hours = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
        return (hours / 24) * Math.PI * 2 - Math.PI / 2;
    }

    // Angle → readable time string (12h format)
    function angleToTimeStr(angle) {
        var hours = ((angle + Math.PI / 2) / (Math.PI * 2)) * 24;
        if (hours < 0) hours += 24;
        if (hours >= 24) hours -= 24;
        var h = Math.floor(hours);
        var m = Math.floor((hours - h) * 60);
        var ampm = h >= 12 ? "PM" : "AM";
        var h12 = h % 12 || 12;
        return h12 + ":" + (m < 10 ? "0" : "") + m + " " + ampm;
    }

    // Normalize angle to [-PI, PI]
    function normAngle(a) {
        while (a > Math.PI) a -= Math.PI * 2;
        while (a < -Math.PI) a += Math.PI * 2;
        return a;
    }

    // Circular moving average smoother
    function smoothArray(arr, windowSize) {
        var half = Math.floor(windowSize / 2);
        var result = [];
        for (var i = 0; i < arr.length; i++) {
            var sum = 0, count = 0;
            for (var j = i - half; j <= i + half; j++) {
                var idx = ((j % arr.length) + arr.length) % arr.length;
                sum += arr[idx];
                count++;
            }
            result.push(sum / count);
        }
        return result;
    }

    function createRadialRing(canvas) {
        var setup = Art.setupCanvas(canvas);
        var ctx = setup.ctx;
        var W = setup.width;
        var H = setup.height;
        var cx = W / 2;
        var cy = H / 2;

        // Ring geometry
        var maxRadius = Math.min(cx, cy) * 0.72;
        var minRadius = maxRadius * 0.42;

        // State
        var data = null;        // [{angle, tempF, time}] sorted by angle
        var smoothedRadii = []; // smoothed radius values matching data indices
        var currentTempF = null;
        var nowAngle = 0;
        var animTime = 0;

        // Hover state
        var hoverPoint = null;

        // D3 scales
        var radiusScale = d3.scaleLinear().range([minRadius, maxRadius]);

        // Clock labels (every 3 hours)
        var CLOCK_LABELS = [
            { label: "12A", angle: -Math.PI / 2 },
            { label: "3A",  angle: -Math.PI / 4 },
            { label: "6A",  angle: 0 },
            { label: "9A",  angle: Math.PI / 4 },
            { label: "12P", angle: Math.PI / 2 },
            { label: "3P",  angle: Math.PI * 3 / 4 },
            { label: "6P",  angle: Math.PI },
            { label: "9P",  angle: -Math.PI * 3 / 4 },
        ];

        // --- Mouse tracking ---
        canvas.addEventListener("mousemove", function (e) {
            if (!data || data.length < 2) { hoverPoint = null; return; }

            var mx = e.clientX - cx;
            var my = e.clientY - cy;
            var dist = Math.sqrt(mx * mx + my * my);

            if (dist < minRadius * 0.5 || dist > maxRadius * 1.3) {
                hoverPoint = null;
                return;
            }

            var mouseAngle = Math.atan2(my, mx);
            var mNorm = normAngle(mouseAngle);
            var bestIdx = 0, bestDist = Infinity;
            for (var i = 0; i < data.length; i++) {
                var dNorm = normAngle(data[i].angle);
                var diff = Math.abs(dNorm - mNorm);
                if (diff > Math.PI) diff = Math.PI * 2 - diff;
                if (diff < bestDist) { bestDist = diff; bestIdx = i; }
            }

            var d = data[bestIdx];
            var r = smoothedRadii[bestIdx] || radiusScale(d.tempF);
            hoverPoint = {
                angle: d.angle, tempF: d.tempF, time: d.time,
                x: Math.cos(d.angle) * r, y: Math.sin(d.angle) * r, r: r
            };
        });

        canvas.addEventListener("mouseleave", function () {
            hoverPoint = null;
        });

        function update(readings) {
            if (!readings || readings.length === 0) {
                data = null;
                smoothedRadii = [];
                return;
            }

            var parsed = readings.map(function (d) {
                var date = new Date(d.timestamp);
                var tempF = (d.unit === "°F") ? d.value : Art.cToF(d.value);
                return { angle: timeToAngle(date), tempF: tempF, time: date };
            });

            parsed.sort(function (a, b) { return a.angle - b.angle; });

            var extent = d3.extent(parsed, function (d) { return d.tempF; });
            var pad = Math.max((extent[1] - extent[0]) * 0.15, 2);
            radiusScale.domain([extent[0] - pad, extent[1] + pad]);

            data = parsed;
            currentTempF = parsed[parsed.length - 1].tempF;

            // Pre-compute smoothed radii (7-point moving average)
            var rawRadii = parsed.map(function (d) { return radiusScale(d.tempF); });
            smoothedRadii = smoothArray(rawRadii, 7);
        }

        function setLiveValue(tempF) {
            currentTempF = tempF;
        }

        function render(dt, now) {
            animTime += dt;
            ctx.clearRect(0, 0, W, H);
            nowAngle = timeToAngle(new Date());

            drawGrid();

            if (!data || data.length < 2) {
                drawLoadingState();
                return;
            }

            drawRing();
            drawCenterDisc();
            if (hoverPoint) {
                drawHover();
            } else {
                drawNowMarker();
            }
            drawCenterValue();
        }

        function drawGrid() {
            ctx.save();
            ctx.translate(cx, cy);

            // Concentric guide circles
            ctx.lineWidth = 0.5;
            var steps = 3;
            for (var i = 1; i <= steps; i++) {
                var r = minRadius + (maxRadius - minRadius) * (i / steps);
                ctx.beginPath();
                ctx.arc(0, 0, r, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(255,255,255,0.03)";
                ctx.stroke();
            }

            // Radial lines at 3h intervals
            ctx.strokeStyle = "rgba(255,255,255,0.04)";
            ctx.lineWidth = 0.5;
            CLOCK_LABELS.forEach(function (cl) {
                ctx.beginPath();
                ctx.moveTo(
                    Math.cos(cl.angle) * (minRadius * 0.85),
                    Math.sin(cl.angle) * (minRadius * 0.85)
                );
                ctx.lineTo(
                    Math.cos(cl.angle) * (maxRadius * 1.06),
                    Math.sin(cl.angle) * (maxRadius * 1.06)
                );
                ctx.stroke();
            });

            // Clock labels
            ctx.fillStyle = "rgba(255,255,255,0.22)";
            ctx.font = "400 11px 'Space Mono', monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            CLOCK_LABELS.forEach(function (cl) {
                var lr = maxRadius * 1.14;
                ctx.fillText(
                    cl.label,
                    Math.cos(cl.angle) * lr,
                    Math.sin(cl.angle) * lr
                );
            });

            ctx.restore();
        }

        function drawRing() {
            ctx.save();
            ctx.translate(cx, cy);

            // Clip to annular region: exclude center disc
            ctx.beginPath();
            ctx.arc(0, 0, maxRadius * 1.2, 0, Math.PI * 2);
            ctx.arc(0, 0, minRadius * 0.88, 0, Math.PI * 2, true);
            ctx.clip();

            // Filled wedges with per-segment color
            for (var i = 0; i < data.length - 1; i++) {
                var d0 = data[i];
                var d1 = data[i + 1];
                if (Math.abs(d1.angle - d0.angle) > Math.PI / 6) continue;

                var r0 = smoothedRadii[i];
                var r1 = smoothedRadii[i + 1];
                var avgTemp = (d0.tempF + d1.tempF) / 2;

                ctx.beginPath();
                ctx.arc(0, 0, minRadius * 0.92, d0.angle, d1.angle);
                ctx.lineTo(Math.cos(d1.angle) * r1, Math.sin(d1.angle) * r1);

                var midAngle = (d0.angle + d1.angle) / 2;
                var midR = (r0 + r1) / 2;
                ctx.quadraticCurveTo(
                    Math.cos(midAngle) * midR * 1.02,
                    Math.sin(midAngle) * midR * 1.02,
                    Math.cos(d0.angle) * r0,
                    Math.sin(d0.angle) * r0
                );
                ctx.closePath();
                ctx.fillStyle = Art.temperatureColorRGBA(avgTemp, 0.2);
                ctx.fill();
            }

            // Smooth outer edge with glow
            if (data.length > 2) {
                var points = [];
                for (var i = 0; i < data.length; i++) {
                    points.push({
                        x: Math.cos(data[i].angle) * smoothedRadii[i],
                        y: Math.sin(data[i].angle) * smoothedRadii[i],
                        temp: data[i].tempF
                    });
                }

                // Glow layer (breathing)
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    var cpx = (prev.x + curr.x) / 2;
                    var cpy = (prev.y + curr.y) / 2;
                    ctx.quadraticCurveTo(prev.x, prev.y, cpx, cpy);
                }
                ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);

                var breathe = 0.08 + 0.04 * Math.sin(animTime / 2000);
                ctx.strokeStyle = Art.temperatureColorRGBA(
                    d3.mean(data, function (d) { return d.tempF; }) || 72, breathe
                );
                ctx.lineWidth = 6;
                ctx.stroke();

                // Main line — per-segment color
                for (var i = 0; i < points.length - 1; i++) {
                    var p0 = points[i];
                    var p1 = points[i + 1];
                    var avgT = (p0.temp + p1.temp) / 2;

                    ctx.beginPath();
                    ctx.moveTo(p0.x, p0.y);
                    var cpx = (p0.x + p1.x) / 2;
                    var cpy = (p0.y + p1.y) / 2;
                    ctx.quadraticCurveTo(p0.x, p0.y, cpx, cpy);
                    ctx.strokeStyle = Art.temperatureColorRGBA(avgT, 0.8);
                    ctx.lineWidth = 1.8;
                    ctx.stroke();
                }
            }

            ctx.restore();
        }

        function drawCenterDisc() {
            ctx.save();
            ctx.translate(cx, cy);

            var discR = minRadius * 0.88;

            // Solid black disc
            ctx.beginPath();
            ctx.arc(0, 0, discR, 0, Math.PI * 2);
            ctx.fillStyle = "#000";
            ctx.fill();

            if (hoverPoint) {
                // Glowing border in hovered temperature color
                ctx.beginPath();
                ctx.arc(0, 0, discR, 0, Math.PI * 2);
                ctx.strokeStyle = Art.temperatureColorRGBA(hoverPoint.tempF, 0.25);
                ctx.lineWidth = 2;
                ctx.stroke();
            } else {
                // Subtle default border
                ctx.beginPath();
                ctx.arc(0, 0, discR, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(255,255,255,0.05)";
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            ctx.restore();
        }

        function drawNowMarker() {
            if (currentTempF === null) return;

            ctx.save();
            ctx.translate(cx, cy);

            var r = radiusScale(currentTempF);
            var x = Math.cos(nowAngle) * r;
            var y = Math.sin(nowAngle) * r;

            // Pulsing glow
            var pulse = 0.8 + 0.2 * Math.sin(animTime / 600);
            var glowSize = 12 + 3 * Math.sin(animTime / 800);

            // Outer glow ring
            ctx.beginPath();
            ctx.arc(x, y, glowSize, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(currentTempF, 0.08 * pulse);
            ctx.fill();

            // Mid glow
            ctx.beginPath();
            ctx.arc(x, y, 7, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(currentTempF, 0.2 * pulse);
            ctx.fill();

            // Core dot
            ctx.beginPath();
            ctx.arc(x, y, 3.5, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColor(currentTempF);
            ctx.globalAlpha = pulse;
            ctx.fill();
            ctx.globalAlpha = 1;

            // Thin line from center
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(x, y);
            ctx.strokeStyle = "rgba(255,255,255,0.08)";
            ctx.lineWidth = 0.5;
            ctx.stroke();

            // "NOW" label
            var labelR = r + 22;
            ctx.fillStyle = "rgba(255,255,255,0.3)";
            ctx.font = "700 9px 'Space Mono', monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("NOW", Math.cos(nowAngle) * labelR, Math.sin(nowAngle) * labelR);

            ctx.restore();
        }

        function drawHover() {
            if (!hoverPoint) return;

            ctx.save();
            ctx.translate(cx, cy);

            var hp = hoverPoint;

            // Radial guide line (dashed)
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(hp.x, hp.y);
            ctx.strokeStyle = "rgba(255,255,255,0.15)";
            ctx.lineWidth = 0.5;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            // Highlight dot
            ctx.beginPath();
            ctx.arc(hp.x, hp.y, 14, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(hp.tempF, 0.15);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(hp.x, hp.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColor(hp.tempF);
            ctx.fill();

            // Tooltip — positioned outward from the point
            var tooltipR = hp.r + 28;
            var tx = Math.cos(hp.angle) * tooltipR;
            var ty = Math.sin(hp.angle) * tooltipR;

            var angleDeg = hp.angle * 180 / Math.PI;
            if (angleDeg > -90 && angleDeg < 90) {
                ctx.textAlign = "left"; tx += 8;
            } else {
                ctx.textAlign = "right"; tx -= 8;
            }
            ctx.textBaseline = "middle";

            // Time
            ctx.fillStyle = "rgba(255,255,255,0.5)";
            ctx.font = "400 11px 'Space Mono', monospace";
            ctx.fillText(angleToTimeStr(hp.angle), tx, ty - 10);

            // Temperature
            ctx.fillStyle = Art.temperatureColor(hp.tempF);
            ctx.font = "700 15px 'Space Mono', monospace";
            ctx.fillText(hp.tempF.toFixed(1) + "°F", tx, ty + 10);

            ctx.restore();
        }

        function drawCenterValue() {
            if (currentTempF === null) return;

            ctx.save();
            ctx.translate(cx, cy);

            var displayTemp = hoverPoint ? hoverPoint.tempF : currentTempF;
            var displayColor = Art.temperatureColor(displayTemp);

            // Size calculations for true center alignment
            var tempSize = Math.round(minRadius * 0.48);
            var unitSize = Math.round(minRadius * 0.14);
            var labelSize = Math.round(minRadius * 0.1);
            var lineGap = tempSize * 0.12;
            var totalH = tempSize * 0.75 + lineGap + unitSize * 0.75 + lineGap + labelSize * 0.75;
            var startY = -totalH / 2;

            // Temperature
            ctx.fillStyle = displayColor;
            ctx.font = "700 " + tempSize + "px 'Space Mono', monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(displayTemp.toFixed(1), 0, startY);

            // °F
            ctx.fillStyle = "rgba(255,255,255,0.3)";
            ctx.font = "400 " + unitSize + "px 'Space Mono', monospace";
            ctx.fillText("°F", 0, startY + tempSize * 0.75 + lineGap);

            // Label: hovered time or subsystem name
            var labelY = startY + tempSize * 0.75 + lineGap + unitSize * 0.75 + lineGap;
            if (hoverPoint) {
                ctx.fillStyle = "rgba(255,255,255,0.25)";
                ctx.font = "400 " + labelSize + "px 'Space Mono', monospace";
                var timeStr = hoverPoint.time.toLocaleTimeString("en-US", {
                    hour: "numeric", minute: "2-digit"
                });
                ctx.fillText(timeStr, 0, labelY);
            } else {
                ctx.fillStyle = "rgba(255,255,255,0.12)";
                ctx.font = "700 " + labelSize + "px 'Space Mono', monospace";
                ctx.letterSpacing = "4px";
                ctx.fillText("AIR", 0, labelY);
            }

            ctx.restore();
        }

        function drawLoadingState() {
            ctx.save();
            ctx.translate(cx, cy);

            var pulse = 0.3 + 0.15 * Math.sin(animTime / 1000);
            ctx.beginPath();
            ctx.arc(0, 0, (minRadius + maxRadius) / 2, 0, Math.PI * 2);
            ctx.strokeStyle = "rgba(255,255,255," + pulse + ")";
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.fillStyle = "rgba(255,255,255,0.15)";
            ctx.font = "400 14px 'Space Mono', monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("loading data...", 0, 0);

            ctx.restore();
        }

        function resize() {
            var s = Art.setupCanvas(canvas);
            ctx = s.ctx;
            W = s.width;
            H = s.height;
            cx = W / 2;
            cy = H / 2;
            maxRadius = Math.min(cx, cy) * 0.72;
            minRadius = maxRadius * 0.42;
            radiusScale.range([minRadius, maxRadius]);
            if (data && data.length > 0) {
                var rawRadii = data.map(function (d) { return radiusScale(d.tempF); });
                smoothedRadii = smoothArray(rawRadii, 7);
            }
        }

        return {
            update: update,
            setLiveValue: setLiveValue,
            render: render,
            resize: resize,
        };
    }

    window.GrowLab.ArtMode.createRadialRing = createRadialRing;

})();
