/**
 * WATER — Irrigation Pulse Strip
 *
 * Renders irrigation events as an EKG-style heartbeat line.
 * Flat baseline with sharp vertical spikes at each pump event.
 * Communicates rhythm and recency — you feel the pulse of the system.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createWaterTimeline = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var rect = container.getBoundingClientRect();
    var margin = { top: 12, right: 8, bottom: 20, left: 8 };
    var width = (rect.width || 240) - margin.left - margin.right;
    var height = (rect.height || 80) - margin.top - margin.bottom;

    var svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var x = d3.scaleTime().range([0, width]);
    var baseline = height * 0.75;
    var spikeTop = 6;

    // X axis
    svg.append("g")
        .attr("class", "axis x-axis")
        .attr("transform", "translate(0," + height + ")");

    // Pulse path (the EKG line)
    svg.append("path")
        .attr("class", "pulse-line")
        .attr("fill", "none")
        .attr("stroke", "var(--accent-cyan)")
        .attr("stroke-width", 1.5)
        .attr("stroke-linejoin", "round");

    // Glow layer (subtle duplicate for luminous feel)
    svg.append("path")
        .attr("class", "pulse-glow")
        .attr("fill", "none")
        .attr("stroke", "var(--accent-cyan)")
        .attr("stroke-width", 4)
        .attr("stroke-linejoin", "round")
        .attr("opacity", 0.08);

    // No-events message
    var noEventsText = svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "var(--text-dim)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "12px")
        .text("")
        .attr("opacity", 0);

    function buildPulsePath(events, xScale) {
        if (events.length === 0) return "";

        // Sort chronologically
        var sorted = events.slice().sort(function (a, b) {
            return a.time - b.time;
        });

        var domain = xScale.domain();
        var spikeWidth = Math.max(2, width * 0.008);
        var parts = [];

        // Start from left edge at baseline
        parts.push("M", xScale(domain[0]), baseline);

        sorted.forEach(function (evt) {
            var cx = xScale(evt.time);

            // Flat line to just before the spike
            parts.push("L", cx - spikeWidth, baseline);

            // Sharp spike up
            parts.push("L", cx, spikeTop);

            // Sharp spike down (slightly past center for asymmetry like a real pulse)
            parts.push("L", cx + spikeWidth * 0.6, baseline + 4);

            // Recovery back to baseline
            parts.push("L", cx + spikeWidth * 1.5, baseline);
        });

        // Flat line to right edge
        parts.push("L", xScale(domain[1]), baseline);

        return parts.join(" ");
    }

    function update(events) {
        if (!events || events.length === 0) {
            svg.select(".pulse-line").attr("d", null);
            svg.select(".pulse-glow").attr("d", null);
            noEventsText.text("No irrigation events").attr("opacity", 1);
            return;
        }

        noEventsText.attr("opacity", 0);

        var parsed = events.map(function (e) {
            return { time: new Date(e.timestamp) };
        });

        // Pad domain to span the full window
        var extent = d3.extent(parsed, function (d) { return d.time; });
        var pad = (extent[1] - extent[0]) * 0.05 || 3600000;
        x.domain([new Date(extent[0] - pad), new Date(extent[1].getTime() + pad)]);

        var pathD = buildPulsePath(parsed, x);

        svg.select(".pulse-line")
            .transition().duration(800)
            .attr("d", pathD);

        svg.select(".pulse-glow")
            .transition().duration(800)
            .attr("d", pathD);

        // Update X axis
        svg.select(".x-axis")
            .transition().duration(400)
            .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%-I%p")));
    }

    return { update: update };
};
