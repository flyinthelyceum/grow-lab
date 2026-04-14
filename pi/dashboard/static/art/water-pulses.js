/**
 * Water Pulse Rings — WATER subsystem irrigation visualization (v2)
 *
 * Irrigation events rendered as expanding ring pulses from the center.
 * Ghost markers at event time positions with pulsing halos.
 * Hover: glowing dot + radial guide; info shown in center disc.
 *
 * Design doc: "irrigation pulses" — event-based, not continuous.
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    // Bright cyan pulse color
    var PULSE_COLOR = { r: 30, g: 210, b: 255 };
    var HOVER_ANGLE_THRESHOLD = 0.045;
    var HOVER_RADIAL_THRESHOLD = 16;

    function pulseRGBA(alpha) {
        return "rgba(" + PULSE_COLOR.r + "," + PULSE_COLOR.g + "," + PULSE_COLOR.b + "," + alpha + ")";
    }

    function timeToAngle(date) {
        var hours = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
        return (hours / 24) * Math.PI * 2 - Math.PI / 2;
    }

    function normAngle(a) {
        while (a > Math.PI) a -= Math.PI * 2;
        while (a < -Math.PI) a += Math.PI * 2;
        return a;
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

    function createWaterPulses(ctx, getCx, getCy, getMaxRadius, getHoverAngle, getMouseDist) {
        var pulses = [];
        var ghostRings = [];
        var animTime = 0;
        var hoverEvent = null;

        function update(irrigationEvents) {
            if (!irrigationEvents || irrigationEvents.length === 0) {
                ghostRings = [];
                return;
            }

            ghostRings = irrigationEvents.map(function (e) {
                var t = new Date(e.timestamp);
                var age = (Date.now() - t.getTime()) / 1000;
                return {
                    angle: timeToAngle(t),
                    brightness: Math.max(0.15, 0.6 * Math.exp(-age / 7200)),
                    time: t,
                    ageMin: Math.round(age / 60),
                };
            });

            // Trigger live pulse for recent events
            irrigationEvents.forEach(function (e) {
                var age = (Date.now() - new Date(e.timestamp).getTime()) / 1000;
                if (age < 30) {
                    triggerPulse();
                }
            });
        }

        function triggerPulse() {
            pulses.push({
                radius: 20,
                alpha: 0.5,
                speed: 1.5,
            });
        }

        function render(dt) {
            animTime += dt;
            var cx = getCx();
            var cy = getCy();
            var maxR = getMaxRadius();

            // Check hover on ghost markers
            hoverEvent = null;
            var hoverAngle = getHoverAngle ? getHoverAngle() : null;
            var mouseDist = getMouseDist ? getMouseDist() : Infinity;

            if (hoverAngle !== null) {
                var markerR = maxR * 0.78;
                var mNorm = normAngle(hoverAngle);
                var bestScore = Infinity;
                for (var gi = 0; gi < ghostRings.length; gi++) {
                    var g = ghostRings[gi];
                    var gNorm = normAngle(g.angle);
                    var diff = Math.abs(gNorm - mNorm);
                    if (diff > Math.PI) diff = Math.PI * 2 - diff;
                    var radialDiff = Math.abs(mouseDist - markerR);
                    if (diff < HOVER_ANGLE_THRESHOLD && radialDiff < HOVER_RADIAL_THRESHOLD) {
                        var score = diff * markerR + radialDiff;
                        if (score < bestScore) {
                            bestScore = score;
                            hoverEvent = g;
                        }
                    }
                }
            }

            ctx.save();
            ctx.translate(cx, cy);

            // Ghost markers — visible dots with pulsing halos
            ghostRings.forEach(function (g) {
                var r = maxR * 0.78;
                var x = Math.cos(g.angle) * r;
                var y = Math.sin(g.angle) * r;
                var isHovered = (hoverEvent === g);
                var b = g.brightness;
                var pulse = 0.7 + 0.3 * Math.sin(animTime / 1200 + g.angle * 3);

                // Outer halo
                ctx.beginPath();
                ctx.arc(x, y, isHovered ? 18 : 10, 0, Math.PI * 2);
                ctx.fillStyle = pulseRGBA((isHovered ? 0.25 : 0.08) * pulse);
                ctx.fill();

                // Core dot
                ctx.beginPath();
                ctx.arc(x, y, isHovered ? 6 : 4, 0, Math.PI * 2);
                ctx.fillStyle = pulseRGBA(b * pulse);
                ctx.fill();

                // Radial tick
                var innerR = r - 8;
                var outerR = r + 8;
                ctx.beginPath();
                ctx.moveTo(Math.cos(g.angle) * innerR, Math.sin(g.angle) * innerR);
                ctx.lineTo(Math.cos(g.angle) * outerR, Math.sin(g.angle) * outerR);
                ctx.strokeStyle = pulseRGBA(b * 0.5 * pulse);
                ctx.lineWidth = isHovered ? 1.5 : 0.8;
                ctx.stroke();

                // Hover: radial guide line (info goes to center disc)
                if (isHovered) {
                    ctx.beginPath();
                    ctx.moveTo(0, 0);
                    ctx.lineTo(x, y);
                    ctx.strokeStyle = pulseRGBA(0.2);
                    ctx.lineWidth = 0.5;
                    ctx.setLineDash([3, 5]);
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            });

            // Expanding pulse rings
            for (var i = pulses.length - 1; i >= 0; i--) {
                var p = pulses[i];
                p.radius += p.speed * (dt / 16);
                p.alpha -= 0.0018 * (dt / 16);

                if (p.alpha <= 0 || p.radius > maxR * 1.5) {
                    pulses.splice(i, 1);
                    continue;
                }

                ctx.beginPath();
                ctx.arc(0, 0, p.radius, 0, Math.PI * 2);
                ctx.strokeStyle = pulseRGBA(p.alpha);
                ctx.lineWidth = 2;
                ctx.stroke();

                ctx.beginPath();
                ctx.arc(0, 0, p.radius, 0, Math.PI * 2);
                ctx.strokeStyle = pulseRGBA(p.alpha * 0.3);
                ctx.lineWidth = 6;
                ctx.stroke();
            }

            ctx.restore();
        }

        return {
            update: update,
            triggerPulse: triggerPulse,
            render: render,
            getHoverEvent: function () { return hoverEvent; },
        };
    }

    window.GrowLab.ArtMode.createWaterPulses = createWaterPulses;

})();
