/**
 * Soil Moisture Arc Gauge
 *
 * Semi-circular gauge that maps moisture percentage to a color arc:
 *   0% (dry) = amber/red
 *   40-70% (optimal) = green
 *   100% (saturated) = cyan/blue
 *
 * Calm, slow transitions. Designed for glancing.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createSoilGauge = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var width = 160;
    var height = 100;
    var radius = 70;
    var thickness = 12;

    var svg = d3.select(container).append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", "translate(" + (width / 2) + "," + (height - 10) + ")");

    // Background arc (full semi-circle, dim)
    var bgArc = d3.arc()
        .innerRadius(radius - thickness)
        .outerRadius(radius)
        .startAngle(-Math.PI / 2)
        .endAngle(Math.PI / 2);

    svg.append("path")
        .attr("d", bgArc)
        .attr("fill", "#1a1a1a");

    // Value arc (filled portion)
    var valueArc = d3.arc()
        .innerRadius(radius - thickness)
        .outerRadius(radius)
        .startAngle(-Math.PI / 2);

    var valuePath = svg.append("path")
        .attr("d", valueArc.endAngle(-Math.PI / 2))
        .attr("fill", "#555");

    // Center label
    var valueText = svg.append("text")
        .attr("text-anchor", "middle")
        .attr("dy", "-0.2em")
        .attr("fill", "var(--text-dim)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "11px")
        .text("--");

    var currentValue = -1;

    function moistureColor(pct) {
        // Dry (0%) = amber, Optimal (50%) = green, Wet (100%) = cyan
        if (pct <= 30) {
            // amber to yellow-green
            var t = pct / 30;
            return d3.interpolateRgb("#ffb300", "#4caf50")(t);
        } else if (pct <= 70) {
            // green zone
            return "#4caf50";
        } else {
            // green to cyan
            var t2 = (pct - 70) / 30;
            return d3.interpolateRgb("#4caf50", "#00bcd4")(t2);
        }
    }

    function update(value) {
        if (value === currentValue) return;
        currentValue = value;

        var pct = Math.max(0, Math.min(100, value));
        var angle = -Math.PI / 2 + (pct / 100) * Math.PI;
        var color = moistureColor(pct);

        valuePath
            .transition()
            .duration(1200)
            .ease(d3.easeCubicInOut)
            .attrTween("d", function () {
                var interpolate = d3.interpolate(
                    valuePath.node().__currentAngle || -Math.PI / 2,
                    angle
                );
                return function (t) {
                    var a = interpolate(t);
                    valuePath.node().__currentAngle = a;
                    return valueArc.endAngle(a)();
                };
            })
            .attr("fill", color);

        valueText
            .transition()
            .duration(400)
            .attr("fill", "var(--text-secondary)")
            .text(pct.toFixed(0) + "%");
    }

    return { update: update };
};
