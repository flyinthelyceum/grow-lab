/**
 * ALERT — History Timeline Strip
 *
 * Renders alert events as dots on a horizontal time axis.
 * Warning events in amber, critical events in red.
 * Hover tooltip shows description and timestamp.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createAlertTimeline = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var rect = container.getBoundingClientRect();
    var margin = { top: 4, right: 8, bottom: 16, left: 8 };
    var width = (rect.width || 600) - margin.left - margin.right;
    var height = (rect.height || 36) - margin.top - margin.bottom;

    var svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var x = d3.scaleTime().range([0, width]);
    var midY = height / 2;

    // Baseline
    svg.append("line")
        .attr("class", "alert-baseline")
        .attr("x1", 0)
        .attr("x2", width)
        .attr("y1", midY)
        .attr("y2", midY)
        .attr("stroke", "var(--border)")
        .attr("stroke-width", 1);

    // X axis
    svg.append("g")
        .attr("class", "axis x-axis")
        .attr("transform", "translate(0," + height + ")");

    // Dot group
    var dotGroup = svg.append("g").attr("class", "alert-dots");

    // Tooltip (hidden by default)
    var tooltip = d3.select(container).append("div")
        .attr("class", "alert-tooltip")
        .style("opacity", 0);

    // No-events message
    var noEventsText = svg.append("text")
        .attr("x", width / 2)
        .attr("y", midY + 2)
        .attr("text-anchor", "middle")
        .attr("fill", "var(--text-dim)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "11px")
        .text("")
        .attr("opacity", 0);

    function formatTime(date) {
        return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    }

    function formatDateTime(date) {
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
            + " " + formatTime(date);
    }

    function update(alerts) {
        if (!alerts || alerts.length === 0) {
            dotGroup.selectAll("circle").remove();
            noEventsText.text("No alerts in window").attr("opacity", 1);
            return;
        }

        noEventsText.attr("opacity", 0);

        var parsed = alerts.map(function (a) {
            return {
                time: new Date(a.timestamp),
                type: a.event_type,
                description: a.description || ""
            };
        });

        var extent = d3.extent(parsed, function (d) { return d.time; });
        var pad = Math.max((extent[1] - extent[0]) * 0.05, 3600000);
        x.domain([new Date(extent[0] - pad), new Date(extent[1].getTime() + pad)]);

        // Update X axis
        svg.select(".x-axis")
            .transition().duration(400)
            .call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat("%-I%p")));

        // Data join
        var dots = dotGroup.selectAll("circle").data(parsed, function (d) {
            return d.time.getTime() + d.type;
        });

        dots.exit().transition().duration(300).attr("r", 0).remove();

        dots.enter().append("circle")
            .attr("cx", function (d) { return x(d.time); })
            .attr("cy", midY)
            .attr("r", 0)
            .attr("fill", function (d) {
                return d.type === "alert_critical" ? "var(--accent-red)" : "var(--accent-amber)";
            })
            .attr("opacity", 0.85)
            .attr("cursor", "pointer")
            .on("mouseover", function (event, d) {
                d3.select(this).transition().duration(150).attr("r", 6);
                tooltip.transition().duration(150).style("opacity", 1);
                var level = d.type === "alert_critical" ? "CRITICAL" : "WARNING";
                var node = tooltip.node();
                node.textContent = "";
                var strong = document.createElement("strong");
                strong.textContent = level;
                node.appendChild(strong);
                node.appendChild(document.createElement("br"));
                node.appendChild(document.createTextNode(d.description));
                node.appendChild(document.createElement("br"));
                var timeSpan = document.createElement("span");
                timeSpan.className = "alert-tooltip-time";
                timeSpan.textContent = formatDateTime(d.time);
                node.appendChild(timeSpan);
                tooltip
                .style("left", (event.offsetX + 10) + "px")
                .style("top", (event.offsetY - 10) + "px");
            })
            .on("mouseout", function () {
                d3.select(this).transition().duration(150).attr("r", 4);
                tooltip.transition().duration(300).style("opacity", 0);
            })
            .transition().duration(500)
            .attr("r", 4);

        dots.transition().duration(500)
            .attr("cx", function (d) { return x(d.time); })
            .attr("fill", function (d) {
                return d.type === "alert_critical" ? "var(--accent-red)" : "var(--accent-amber)";
            });
    }

    return { update: update };
};
