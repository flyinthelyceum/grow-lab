/**
 * Radial Thermal Ring — AIR subsystem art visualization (v4)
 *
 * 24h temperature data rendered in polar coordinates on canvas.
 * Midnight at top (12 o'clock), noon at bottom.
 * Radius = stable outer band with restrained temperature wobble.
 * Color shifts deep blue → teal → warm amber along the ring.
 *
 * Features:
 *  - Smoothed ring edge (9-point moving average + quadratic curves)
 *  - Radial gradient fills per wedge for depth
 *  - Center disc with current value or layer-override content
 *  - Pulsing "now" marker that tracks current time
 *  - Hover interaction: mouse over ring reveals time + temp
 *  - 8 clock labels (3-hour intervals)
 *  - Breathing glow animation on outer edge
 *  - Center override API for humidity/water hover info
 *
 * Uses D3 for math (scales, extent), Canvas 2D for rendering.
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

        var maxRadius = Math.min(cx, cy) * 0.72;
        var minRadius = maxRadius * 0.42;

        var data = null;
        var smoothedRadii = [];
        var currentTempF = null;
        var nowAngle = 0;
        var animTime = 0;

        var hoverPoint = null;
        var mouseInCanvas = false;
        var mouseX = 0, mouseY = 0;

        var radiusScale = d3.scaleLinear();
        var baseOuterRadius = minRadius + (maxRadius - minRadius) * 0.68;
        var wobbleAmplitude = (maxRadius - minRadius) * 0.22;

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

        // Center override: set by controller when humidity/water is hovered
        var _centerOverride = null;

        canvas.addEventListener("mousemove", function (e) {
            mouseInCanvas = true;
            mouseX = e.clientX;
            mouseY = e.clientY;
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
            mouseInCanvas = false;
            hoverPoint = null;
        });

        function getHoverAngle() {
            if (!mouseInCanvas) return null;
            return Math.atan2(mouseY - cy, mouseX - cx);
        }

        function getMouseDist() {
            if (!mouseInCanvas) return Infinity;
            var mx = mouseX - cx;
            var my = mouseY - cy;
            return Math.sqrt(mx * mx + my * my);
        }

        function setCenterOverride(override) { _centerOverride = override; }

        function update(readings) {
            if (!readings || readings.length === 0) { data = null; smoothedRadii = []; return; }

            var parsed = readings.map(function (d) {
                var date = new Date(d.timestamp);
                var tempF = (d.unit === "°F") ? d.value : Art.cToF(d.value);
                return { angle: timeToAngle(date), tempF: tempF, time: date };
            });
            parsed.sort(function (a, b) { return a.angle - b.angle; });

            var tempMean = d3.mean(parsed, function (d) { return d.tempF; }) || 72;
            var maxDeviation = d3.max(parsed, function (d) {
                return Math.abs(d.tempF - tempMean);
            }) || 0;
            var deviationSpan = Math.max(maxDeviation * 1.15, 3.5);

            radiusScale
                .domain([tempMean - deviationSpan, tempMean + deviationSpan])
                .range([baseOuterRadius - wobbleAmplitude, baseOuterRadius + wobbleAmplitude])
                .clamp(true);

            data = parsed;
            currentTempF = parsed[parsed.length - 1].tempF;

            var rawRadii = parsed.map(function (d) { return radiusScale(d.tempF); });
            smoothedRadii = smoothArray(rawRadii, 9);
        }

        function setLiveValue(tempF) { currentTempF = tempF; }

        function render(dt, now) {
            animTime += dt;
            ctx.clearRect(0, 0, W, H);
            nowAngle = timeToAngle(new Date());

            drawGrid();

            if (!data || data.length < 2) { drawLoadingState(); return; }

            drawRing();
            drawCenterDisc();
            if (hoverPoint && !_centerOverride) {
                drawHover();
            } else if (!hoverPoint) {
                drawNowMarker();
            }
            drawCenterValue();
        }

        function drawGrid() {
            ctx.save();
            ctx.translate(cx, cy);

            ctx.lineWidth = 0.5;
            var steps = 3;
            for (var i = 1; i <= steps; i++) {
                var r = minRadius + (maxRadius - minRadius) * (i / steps);
                ctx.beginPath();
                ctx.arc(0, 0, r, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(255,255,255,0.03)";
                ctx.stroke();
            }

            ctx.strokeStyle = "rgba(255,255,255,0.04)";
            ctx.lineWidth = 0.5;
            CLOCK_LABELS.forEach(function (cl) {
                ctx.beginPath();
                ctx.moveTo(Math.cos(cl.angle) * (minRadius * 0.85), Math.sin(cl.angle) * (minRadius * 0.85));
                ctx.lineTo(Math.cos(cl.angle) * (maxRadius * 1.06), Math.sin(cl.angle) * (maxRadius * 1.06));
                ctx.stroke();
            });

            ctx.fillStyle = "rgba(255,255,255,0.22)";
            ctx.font = "400 11px 'Space Mono', monospace";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            CLOCK_LABELS.forEach(function (cl) {
                var lr = maxRadius * 1.14;
                ctx.fillText(cl.label, Math.cos(cl.angle) * lr, Math.sin(cl.angle) * lr);
            });

            ctx.restore();
        }

        function drawRing() {
            ctx.save();
            ctx.translate(cx, cy);

            ctx.beginPath();
            ctx.arc(0, 0, maxRadius * 1.2, 0, Math.PI * 2);
            ctx.arc(0, 0, minRadius * 0.88, 0, Math.PI * 2, true);
            ctx.clip();

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

                var grad = ctx.createRadialGradient(0, 0, minRadius * 0.92, 0, 0, midR);
                grad.addColorStop(0, Art.temperatureColorRGBA(avgTemp, 0.12));
                grad.addColorStop(1, Art.temperatureColorRGBA(avgTemp, 0.45));
                ctx.fillStyle = grad;
                ctx.fill();
            }

            if (data.length > 2) {
                var points = [];
                for (var i = 0; i < data.length; i++) {
                    points.push({
                        x: Math.cos(data[i].angle) * smoothedRadii[i],
                        y: Math.sin(data[i].angle) * smoothedRadii[i],
                        temp: data[i].tempF
                    });
                }

                var breathe = 0.08 + 0.03 * Math.sin(animTime / 2600);
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                for (var i = 1; i < points.length; i++) {
                    var prev = points[i - 1];
                    var curr = points[i];
                    ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
                }
                ctx.strokeStyle = Art.temperatureColorRGBA(
                    d3.mean(data, function(d) { return d.tempF; }) || 72, breathe
                );
                ctx.lineWidth = 5;
                ctx.stroke();

                for (var i = 0; i < points.length - 1; i++) {
                    var p0 = points[i];
                    var p1 = points[i + 1];
                    var avgT = (p0.temp + p1.temp) / 2;

                    ctx.beginPath();
                    ctx.moveTo(p0.x, p0.y);
                    ctx.quadraticCurveTo(p0.x, p0.y, (p0.x + p1.x) / 2, (p0.y + p1.y) / 2);
                    ctx.strokeStyle = Art.temperatureColorRGBA(avgT, 0.75);
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                }
            }

            ctx.restore();
        }

        function drawCenterDisc() {
            ctx.save();
            ctx.translate(cx, cy);

            var discR = minRadius * 0.88;

            ctx.beginPath();
            ctx.arc(0, 0, discR, 0, Math.PI * 2);
            ctx.fillStyle = "#000";
            ctx.fill();

            if (hoverPoint) {
                ctx.beginPath();
                ctx.arc(0, 0, discR, 0, Math.PI * 2);
                ctx.strokeStyle = Art.temperatureColorRGBA(hoverPoint.tempF, 0.35);
                ctx.lineWidth = 2;
                ctx.stroke();
            } else {
                ctx.beginPath();
                ctx.arc(0, 0, discR, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(255,255,255,0.06)";
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

            var pulse = 0.8 + 0.2 * Math.sin(animTime / 600);
            var glowSize = 14 + 4 * Math.sin(animTime / 800);

            ctx.beginPath();
            ctx.arc(x, y, glowSize, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(currentTempF, 0.1 * pulse);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(x, y, 8, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(currentTempF, 0.25 * pulse);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(x, y, 4, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColor(currentTempF);
            ctx.globalAlpha = pulse;
            ctx.fill();
            ctx.globalAlpha = 1;

            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(x, y);
            ctx.strokeStyle = Art.temperatureColorRGBA(currentTempF, 0.1);
            ctx.lineWidth = 0.5;
            ctx.stroke();

            var labelR = r + 24;
            ctx.fillStyle = "rgba(255,255,255,0.35)";
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

            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.lineTo(hp.x, hp.y);
            ctx.strokeStyle = Art.temperatureColorRGBA(hp.tempF, 0.2);
            ctx.lineWidth = 0.5;
            ctx.setLineDash([4, 4]);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.beginPath();
            ctx.arc(hp.x, hp.y, 16, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColorRGBA(hp.tempF, 0.2);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(hp.x, hp.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = Art.temperatureColor(hp.tempF);
            ctx.fill();

            var tooltipR = hp.r + 30;
            var tx = Math.cos(hp.angle) * tooltipR;
            var ty = Math.sin(hp.angle) * tooltipR;

            var angleDeg = hp.angle * 180 / Math.PI;
            if (angleDeg > -90 && angleDeg < 90) {
                ctx.textAlign = "left"; tx += 8;
            } else {
                ctx.textAlign = "right"; tx -= 8;
            }
            ctx.textBaseline = "middle";

            ctx.fillStyle = "rgba(255,255,255,0.5)";
            ctx.font = "400 11px 'Space Mono', monospace";
            ctx.fillText(angleToTimeStr(hp.angle), tx, ty - 10);

            ctx.fillStyle = Art.temperatureColor(hp.tempF);
            ctx.font = "700 15px 'Space Mono', monospace";
            ctx.fillText(hp.tempF.toFixed(1) + "°F", tx, ty + 10);

            ctx.restore();
        }

        function drawCenterValue() {
            if (currentTempF === null && !_centerOverride) return;

            ctx.save();
            ctx.translate(cx, cy);

            var tempSize = Math.round(minRadius * 0.48);
            var unitSize = Math.round(minRadius * 0.14);
            var labelSize = Math.round(minRadius * 0.1);
            var lineGap = tempSize * 0.12;
            var totalH = tempSize * 0.75 + lineGap + unitSize * 0.75 + lineGap + labelSize * 0.75;
            var startY = -totalH / 2;

            if (_centerOverride) {
                ctx.fillStyle = _centerOverride.color;
                ctx.font = "700 " + tempSize + "px 'Space Mono', monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillText(_centerOverride.value, 0, startY);

                ctx.fillStyle = "rgba(255,255,255,0.3)";
                ctx.font = "400 " + unitSize + "px 'Space Mono', monospace";
                ctx.fillText(_centerOverride.unit, 0, startY + tempSize * 0.75 + lineGap);

                var labelY = startY + tempSize * 0.75 + lineGap + unitSize * 0.75 + lineGap;
                ctx.fillStyle = _centerOverride.labelColor || "rgba(255,255,255,0.25)";
                ctx.font = "400 " + labelSize + "px 'Space Mono', monospace";
                ctx.fillText(_centerOverride.label, 0, labelY);
            } else {
                var displayTemp = hoverPoint ? hoverPoint.tempF : currentTempF;
                var displayColor = Art.temperatureColor(displayTemp);

                ctx.fillStyle = displayColor;
                ctx.font = "700 " + tempSize + "px 'Space Mono', monospace";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                ctx.fillText(displayTemp.toFixed(1), 0, startY);

                ctx.fillStyle = "rgba(255,255,255,0.3)";
                ctx.font = "400 " + unitSize + "px 'Space Mono', monospace";
                ctx.fillText("°F", 0, startY + tempSize * 0.75 + lineGap);

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
                    ctx.fillText("AIR", 0, labelY);
                }
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
            ctx = s.ctx; W = s.width; H = s.height;
            cx = W / 2; cy = H / 2;
            maxRadius = Math.min(cx, cy) * 0.72;
            minRadius = maxRadius * 0.42;
            baseOuterRadius = minRadius + (maxRadius - minRadius) * 0.68;
            wobbleAmplitude = (maxRadius - minRadius) * 0.22;
            if (data && data.length > 0) {
                var rawRadii = data.map(function (d) { return radiusScale(d.tempF); });
                smoothedRadii = smoothArray(rawRadii, 9);
            }
        }

        return {
            update: update,
            setLiveValue: setLiveValue,
            render: render,
            resize: resize,
            setCenterOverride: setCenterOverride,
            getHoverAngle: getHoverAngle,
            getMouseDist: getMouseDist,
            getHoverPoint: function () { return hoverPoint; },
            getMinRadius: function () { return minRadius; },
            getMaxRadius: function () { return maxRadius; },
        };
    }

    window.GrowLab.ArtMode.createRadialRing = createRadialRing;

})();
