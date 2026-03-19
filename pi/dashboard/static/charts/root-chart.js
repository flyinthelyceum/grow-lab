/**
 * ROOT — Drift Stability Sparklines
 *
 * pH and EC as stacked mini-charts with target bands.
 * MonotoneX curves preserve monotonicity to show true drift.
 * Tight Y-axis padding emphasizes small drifts that matter.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createRootChart = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var rect = container.getBoundingClientRect();
    var margin = { top: 4, right: 8, bottom: 20, left: 40 };
    var fullWidth = (rect.width || 240) - margin.left - margin.right;
    var fullHeight = (rect.height || 80) - margin.top - margin.bottom;
    var chartGap = 8;
    var chartHeight = (fullHeight - chartGap) / 2;

    var svg = d3.select(container).append("svg")
        .attr("width", fullWidth + margin.left + margin.right)
        .attr("height", fullHeight + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // pH sub-chart (top)
    var phGroup = svg.append("g").attr("class", "ph-chart");
    var phX = d3.scaleTime().range([0, fullWidth]);
    var phY = d3.scaleLinear().range([chartHeight, 0]);

    // pH target band (5.8 - 6.5)
    var phBand = phGroup.append("rect")
        .attr("class", "target-band")
        .attr("x", 0).attr("width", fullWidth)
        .attr("fill", "var(--accent-green)")
        .attr("opacity", 0.06);

    phGroup.append("path").attr("class", "ph-line");
    phGroup.append("g").attr("class", "axis ph-y-axis");
    phGroup.append("text")
        .attr("x", -4).attr("y", -2)
        .attr("text-anchor", "end")
        .attr("fill", "var(--accent-green)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "10px")
        .text("pH");

    // EC sub-chart (bottom)
    var ecOffset = chartHeight + chartGap;
    var ecGroup = svg.append("g")
        .attr("class", "ec-chart")
        .attr("transform", "translate(0," + ecOffset + ")");
    var ecX = d3.scaleTime().range([0, fullWidth]);
    var ecY = d3.scaleLinear().range([chartHeight, 0]);

    // EC target band (800 - 1600 µS/cm)
    var ecBand = ecGroup.append("rect")
        .attr("class", "target-band")
        .attr("x", 0).attr("width", fullWidth)
        .attr("fill", "var(--accent-green)")
        .attr("opacity", 0.06);

    ecGroup.append("path").attr("class", "ec-line");
    ecGroup.append("g").attr("class", "axis ec-y-axis");
    ecGroup.append("g").attr("class", "axis ec-x-axis")
        .attr("transform", "translate(0," + chartHeight + ")");
    ecGroup.append("text")
        .attr("x", -4).attr("y", -2)
        .attr("text-anchor", "end")
        .attr("fill", "var(--accent-green)")
        .attr("font-family", "var(--font-data)")
        .attr("font-size", "10px")
        .attr("opacity", 0.6)
        .text("EC");

    var curveFn = d3.curveMonotoneX;

    // Hover crosshairs for each sub-chart
    var phHover = null;
    var ecHover = null;
    if (window.GrowLab.addChartHover) {
        phHover = window.GrowLab.addChartHover({
            svg: phGroup, width: fullWidth, height: chartHeight, xScale: phX
        });
        ecHover = window.GrowLab.addChartHover({
            svg: ecGroup, width: fullWidth, height: chartHeight, xScale: ecX
        });
    }

    function update(phData, ecData) {
        // pH
        if (phData && phData.length > 0) {
            var parsedPh = phData.map(function (d) {
                return { time: new Date(d.timestamp), value: d.value };
            });

            phX.domain(d3.extent(parsedPh, function (d) { return d.time; }));
            var phExtent = d3.extent(parsedPh, function (d) { return d.value; });
            var phPad = Math.max((phExtent[1] - phExtent[0]) * 0.2, 0.2);
            phY.domain([phExtent[0] - phPad, phExtent[1] + phPad]);

            // Update target band position
            var bandTop = phY(6.5);
            var bandBottom = phY(5.8);
            phBand
                .attr("y", Math.min(bandTop, bandBottom))
                .attr("height", Math.abs(bandBottom - bandTop));

            var phLine = d3.line()
                .x(function (d) { return phX(d.time); })
                .y(function (d) { return phY(d.value); })
                .curve(curveFn);

            phGroup.select(".ph-line")
                .datum(parsedPh)
                .transition().duration(800)
                .attr("d", phLine)
                .attr("fill", "none")
                .attr("stroke", "var(--accent-green)")
                .attr("stroke-width", 1.5);

            phGroup.select(".ph-y-axis")
                .transition().duration(400)
                .call(d3.axisLeft(phY).ticks(3).tickFormat(function (d) { return d.toFixed(1); }));

            if (phHover) {
                phHover.update([{
                    data: parsedPh, yScale: phY, label: "pH",
                    color: "var(--accent-green)",
                    format: function (v) { return v.toFixed(2); }
                }]);
            }
        }

        // EC
        if (ecData && ecData.length > 0) {
            var parsedEc = ecData.map(function (d) {
                return { time: new Date(d.timestamp), value: d.value };
            });

            ecX.domain(d3.extent(parsedEc, function (d) { return d.time; }));
            var ecExtent = d3.extent(parsedEc, function (d) { return d.value; });
            var ecPad = Math.max((ecExtent[1] - ecExtent[0]) * 0.2, 50);
            ecY.domain([ecExtent[0] - ecPad, ecExtent[1] + ecPad]);

            // Update target band position
            var ecBandTop = ecY(1600);
            var ecBandBottom = ecY(800);
            ecBand
                .attr("y", Math.min(ecBandTop, ecBandBottom))
                .attr("height", Math.abs(ecBandBottom - ecBandTop));

            var ecLine = d3.line()
                .x(function (d) { return ecX(d.time); })
                .y(function (d) { return ecY(d.value); })
                .curve(curveFn);

            ecGroup.select(".ec-line")
                .datum(parsedEc)
                .transition().duration(800)
                .attr("d", ecLine)
                .attr("fill", "none")
                .attr("stroke", "var(--accent-green)")
                .attr("stroke-width", 1.5)
                .attr("opacity", 0.7);

            ecGroup.select(".ec-y-axis")
                .transition().duration(400)
                .call(d3.axisLeft(ecY).ticks(3));

            ecGroup.select(".ec-x-axis")
                .transition().duration(400)
                .call(d3.axisBottom(ecX).ticks(4).tickFormat(d3.timeFormat("%-I%p")));

            if (ecHover) {
                ecHover.update([{
                    data: parsedEc, yScale: ecY, label: "EC",
                    color: "var(--accent-green)",
                    format: function (v) { return v.toFixed(0) + " µS/cm"; }
                }]);
            }
        }
    }

    return { update: update };
};
