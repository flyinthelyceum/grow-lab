/**
 * Chart Hover — Shared crosshair + tooltip for Observatory D3 charts.
 *
 * Adds a vertical guide line and value tooltip on mousemove.
 * Supports single and dual-axis charts.
 *
 * Usage:
 *   var hover = GrowLab.addChartHover({ svg, width, height });
 *   hover.update([{ data, yScale, label, color, format }]);
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.addChartHover = function (opts) {
    "use strict";

    var svg = opts.svg;
    var width = opts.width;
    var height = opts.height;
    var xScale = opts.xScale;

    var datasets = [];

    // Hover elements
    var hoverGroup = svg.append("g")
        .attr("class", "chart-hover")
        .style("display", "none");

    // Vertical guide line
    hoverGroup.append("line")
        .attr("class", "hover-guide")
        .attr("y1", 0)
        .attr("y2", height)
        .attr("stroke", "rgba(255,255,255,0.2)")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "3,3");

    // Tooltip background
    var tooltipGroup = hoverGroup.append("g").attr("class", "hover-tooltip");

    var tooltipBg = tooltipGroup.append("rect")
        .attr("rx", 3)
        .attr("ry", 3)
        .attr("fill", "rgba(0,0,0,0.85)")
        .attr("stroke", "rgba(255,255,255,0.1)")
        .attr("stroke-width", 0.5);

    // Time label
    var timeText = tooltipGroup.append("text")
        .attr("class", "hover-time")
        .attr("fill", "rgba(255,255,255,0.5)")
        .attr("font-family", "var(--font-data, 'Space Mono', monospace)")
        .attr("font-size", "10px");

    // Value labels (up to 4)
    var valueTexts = [];
    for (var i = 0; i < 4; i++) {
        valueTexts.push(tooltipGroup.append("text")
            .attr("class", "hover-value-" + i)
            .attr("font-family", "var(--font-data, 'Space Mono', monospace)")
            .attr("font-size", "11px")
            .attr("font-weight", "700"));
    }

    // Dots on data lines
    var dots = [];
    for (var j = 0; j < 4; j++) {
        dots.push(hoverGroup.append("circle")
            .attr("r", 3.5)
            .style("display", "none"));
    }

    // Invisible overlay to capture mouse events
    var overlay = svg.append("rect")
        .attr("class", "hover-overlay")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "none")
        .attr("pointer-events", "all");

    var bisector = d3.bisector(function (d) { return d.time; }).left;

    function formatTime(date) {
        return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    }

    overlay.on("mousemove", function (event) {
        if (datasets.length === 0) return;

        var coords = d3.pointer(event);
        var mouseX = coords[0];
        var hoverTime = xScale.invert(mouseX);

        hoverGroup.style("display", null);

        // Position guide line
        hoverGroup.select(".hover-guide")
            .attr("x1", mouseX)
            .attr("x2", mouseX);

        // Find nearest points in each dataset
        var lines = [];
        datasets.forEach(function (ds, idx) {
            if (!ds.data || ds.data.length === 0) return;

            var i = bisector(ds.data, hoverTime, 1);
            var d0 = ds.data[i - 1];
            var d1 = ds.data[i];
            if (!d0 && !d1) return;

            var nearest;
            if (!d0) {
                nearest = d1;
            } else if (!d1) {
                nearest = d0;
            } else {
                nearest = (hoverTime - d0.time) < (d1.time - hoverTime) ? d0 : d1;
            }

            var px = xScale(nearest.time);
            var py = ds.yScale(nearest.value);
            var formatted = ds.format ? ds.format(nearest.value) : nearest.value.toFixed(1);

            lines.push({
                idx: idx,
                label: ds.label,
                color: ds.color,
                value: formatted,
                px: px,
                py: py,
                time: nearest.time,
            });
        });

        if (lines.length === 0) {
            hoverGroup.style("display", "none");
            return;
        }

        // Position dots
        for (var di = 0; di < dots.length; di++) {
            if (di < lines.length) {
                dots[di]
                    .attr("cx", lines[di].px)
                    .attr("cy", lines[di].py)
                    .attr("fill", lines[di].color)
                    .style("display", null);
            } else {
                dots[di].style("display", "none");
            }
        }

        // Build tooltip content
        var timeStr = formatTime(lines[0].time);
        timeText.text(timeStr);

        var lineHeight = 14;
        var padding = 6;
        var tooltipH = padding + 14 + lines.length * lineHeight + padding;
        var tooltipW = 0;

        // Measure text widths
        var tempNode = timeText.node();
        var timeW = tempNode ? tempNode.getComputedTextLength() : 60;
        tooltipW = Math.max(tooltipW, timeW);

        for (var vi = 0; vi < valueTexts.length; vi++) {
            if (vi < lines.length) {
                var txt = lines[vi].label + ": " + lines[vi].value;
                valueTexts[vi]
                    .text(txt)
                    .attr("fill", lines[vi].color)
                    .style("display", null);
                var vNode = valueTexts[vi].node();
                if (vNode) tooltipW = Math.max(tooltipW, vNode.getComputedTextLength());
            } else {
                valueTexts[vi].style("display", "none");
            }
        }

        tooltipW += padding * 2 + 4;

        // Position tooltip — flip sides to stay in bounds
        var tx = mouseX + 12;
        if (tx + tooltipW > width) {
            tx = mouseX - tooltipW - 12;
        }
        var ty = Math.max(0, Math.min(height - tooltipH, (lines[0].py || height / 2) - tooltipH / 2));

        tooltipGroup.attr("transform", "translate(" + tx + "," + ty + ")");

        tooltipBg
            .attr("width", tooltipW)
            .attr("height", tooltipH);

        timeText
            .attr("x", padding)
            .attr("y", padding + 10);

        for (var li = 0; li < lines.length; li++) {
            valueTexts[li]
                .attr("x", padding)
                .attr("y", padding + 14 + (li + 1) * lineHeight);
        }
    });

    overlay.on("mouseleave", function () {
        hoverGroup.style("display", "none");
    });

    function update(newDatasets) {
        datasets = newDatasets || [];
    }

    return { update: update };
};
