/**
 * LIGHT — Step Area with Photoperiod Band
 *
 * Light follows on/off daily cycles. StepAfter curve shows
 * discrete transitions. Amber color, shaded photoperiod window.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createLightChart = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var rect = container.getBoundingClientRect();
    var margin = { top: 8, right: 8, bottom: 20, left: 40 };
    var width = (rect.width || 240) - margin.left - margin.right;
    var height = (rect.height || 80) - margin.top - margin.bottom;

    var svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var x = d3.scaleTime().range([0, width]);
    var y = d3.scaleLinear().range([height, 0]);

    // Grid
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x).ticks(4).tickSize(-height).tickFormat(""));

    // Area (filled step)
    svg.append("path").attr("class", "light-area");

    // Line (step)
    svg.append("path").attr("class", "light-line");

    // Axes
    svg.append("g").attr("class", "axis x-axis")
        .attr("transform", "translate(0," + height + ")");
    svg.append("g").attr("class", "axis y-axis");

    // No-data message
    var noDataText = svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "var(--text-dim)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "12px")
        .text("")
        .attr("opacity", 0);

    function update(data) {
        if (!data || data.length === 0) {
            svg.select(".light-line").attr("d", null);
            svg.select(".light-area").attr("d", null);
            noDataText.text("No light data").attr("opacity", 1);
            return;
        }

        noDataText.attr("opacity", 0);

        var parsed = data.map(function (d) {
            return { time: new Date(d.timestamp), value: d.value };
        });

        x.domain(d3.extent(parsed, function (d) { return d.time; }));
        var yMax = d3.max(parsed, function (d) { return d.value; }) || 255;
        y.domain([0, Math.max(yMax * 1.1, 10)]);

        // Step curve for discrete on/off transitions
        var line = d3.line()
            .x(function (d) { return x(d.time); })
            .y(function (d) { return y(d.value); })
            .curve(d3.curveStepAfter);

        var area = d3.area()
            .x(function (d) { return x(d.time); })
            .y0(height)
            .y1(function (d) { return y(d.value); })
            .curve(d3.curveStepAfter);

        svg.select(".light-line")
            .datum(parsed)
            .transition().duration(800)
            .attr("d", line)
            .attr("fill", "none")
            .attr("stroke", "var(--accent-amber)")
            .attr("stroke-width", 1.5);

        svg.select(".light-area")
            .datum(parsed)
            .transition().duration(800)
            .attr("d", area)
            .attr("fill", "var(--accent-amber)")
            .attr("opacity", 0.12);

        svg.select(".x-axis")
            .transition().duration(400)
            .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%-I%p")));

        svg.select(".y-axis")
            .transition().duration(400)
            .call(d3.axisLeft(y).ticks(4));
    }

    return { update: update };
};
