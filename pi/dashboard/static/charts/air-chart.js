/**
 * AIR — Dual-Axis Layered Waveform
 *
 * Temperature (left Y, °F) and humidity (right Y, %) overlaid.
 * CatmullRom curves for organic, breathing feel.
 * Temperature in primary text color, humidity in cyan at low opacity.
 */

window.GrowLab = window.GrowLab || {};

window.GrowLab.createAirChart = function (containerId) {
    "use strict";

    var container = document.getElementById(containerId);
    if (!container) return null;

    var rect = container.getBoundingClientRect();
    var margin = { top: 8, right: 40, bottom: 20, left: 40 };
    var width = (rect.width || 240) - margin.left - margin.right;
    var height = (rect.height || 80) - margin.top - margin.bottom;

    var svg = d3.select(container).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var x = d3.scaleTime().range([0, width]);
    var yTemp = d3.scaleLinear().range([height, 0]);
    var yHum = d3.scaleLinear().range([height, 0]);

    // Grid
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(x).ticks(4).tickSize(-height).tickFormat(""));

    // Temperature target band (65-80°F optimal)
    var tempBand = svg.append("rect")
        .attr("class", "target-band")
        .attr("x", 0).attr("width", width)
        .attr("fill", "var(--text-primary)")
        .attr("opacity", 0.04);

    // Humidity target band (40-70%)
    var humBand = svg.append("rect")
        .attr("class", "target-band")
        .attr("x", 0).attr("width", width)
        .attr("fill", "var(--accent-cyan)")
        .attr("opacity", 0.04);

    // Humidity area (behind temperature)
    svg.append("path").attr("class", "hum-area");
    svg.append("path").attr("class", "hum-line");

    // Temperature area
    svg.append("path").attr("class", "temp-area");
    svg.append("path").attr("class", "temp-line");

    // Axes
    svg.append("g").attr("class", "axis x-axis")
        .attr("transform", "translate(0," + height + ")");
    svg.append("g").attr("class", "axis y-axis-left");
    svg.append("g").attr("class", "axis y-axis-right")
        .attr("transform", "translate(" + width + ",0)");

    // Hover crosshair
    var hover = null;
    if (window.GrowLab.addChartHover) {
        hover = window.GrowLab.addChartHover({
            svg: svg, width: width, height: height, xScale: x
        });
    }

    function update(tempData, humData) {
        if ((!tempData || tempData.length === 0) && (!humData || humData.length === 0)) return;

        var parsedTemp = (tempData || []).map(function (d) {
            return { time: new Date(d.timestamp), value: d.value };
        });
        var parsedHum = (humData || []).map(function (d) {
            return { time: new Date(d.timestamp), value: d.value };
        });

        // Shared X domain
        var allTimes = parsedTemp.map(function (d) { return d.time; })
            .concat(parsedHum.map(function (d) { return d.time; }));
        x.domain(d3.extent(allTimes));

        // Temperature Y
        if (parsedTemp.length > 0) {
            var tExtent = d3.extent(parsedTemp, function (d) { return d.value; });
            var tPad = (tExtent[1] - tExtent[0]) * 0.15 || 2;
            yTemp.domain([tExtent[0] - tPad, tExtent[1] + tPad]);
        }

        // Humidity Y (always 0-100)
        yHum.domain([0, 100]);

        var curveFn = d3.curveCatmullRom.alpha(0.5);

        // Update target bands
        if (parsedTemp.length > 0) {
            var tBandTop = yTemp(80);
            var tBandBot = yTemp(65);
            tempBand.attr("y", Math.min(tBandTop, tBandBot))
                .attr("height", Math.abs(tBandBot - tBandTop));
        }

        var hBandTop = yHum(70);
        var hBandBot = yHum(40);
        humBand.attr("y", Math.min(hBandTop, hBandBot))
            .attr("height", Math.abs(hBandBot - hBandTop));

        // Temperature line + area
        if (parsedTemp.length > 0) {
            var tempLine = d3.line()
                .x(function (d) { return x(d.time); })
                .y(function (d) { return yTemp(d.value); })
                .curve(curveFn);

            var tempArea = d3.area()
                .x(function (d) { return x(d.time); })
                .y0(height)
                .y1(function (d) { return yTemp(d.value); })
                .curve(curveFn);

            svg.select(".temp-line")
                .datum(parsedTemp)
                .transition().duration(800)
                .attr("d", tempLine)
                .attr("fill", "none")
                .attr("stroke", "var(--text-primary)")
                .attr("stroke-width", 1.5);

            svg.select(".temp-area")
                .datum(parsedTemp)
                .transition().duration(800)
                .attr("d", tempArea)
                .attr("fill", "var(--text-primary)")
                .attr("opacity", 0.08);
        }

        // Humidity line + area
        if (parsedHum.length > 0) {
            var humLine = d3.line()
                .x(function (d) { return x(d.time); })
                .y(function (d) { return yHum(d.value); })
                .curve(curveFn);

            var humArea = d3.area()
                .x(function (d) { return x(d.time); })
                .y0(height)
                .y1(function (d) { return yHum(d.value); })
                .curve(curveFn);

            svg.select(".hum-line")
                .datum(parsedHum)
                .transition().duration(800)
                .attr("d", humLine)
                .attr("fill", "none")
                .attr("stroke", "var(--accent-cyan)")
                .attr("stroke-width", 1)
                .attr("opacity", 0.4);

            svg.select(".hum-area")
                .datum(parsedHum)
                .transition().duration(800)
                .attr("d", humArea)
                .attr("fill", "var(--accent-cyan)")
                .attr("opacity", 0.05);
        }

        // X axis
        svg.select(".x-axis")
            .transition().duration(400)
            .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%-I%p")));

        // Left Y axis (temperature, °F)
        svg.select(".y-axis-left")
            .transition().duration(400)
            .call(d3.axisLeft(yTemp).ticks(4).tickFormat(function (d) { return d.toFixed(0) + "°"; }));

        // Right Y axis (humidity, %)
        svg.select(".y-axis-right")
            .transition().duration(400)
            .call(d3.axisRight(yHum).ticks(4).tickFormat(function (d) { return d + "%"; }));

        // Update hover datasets
        if (hover) {
            var hoverSets = [];
            if (parsedTemp.length > 0) {
                hoverSets.push({
                    data: parsedTemp, yScale: yTemp, label: "Temp",
                    color: "var(--text-primary)",
                    format: function (v) { return v.toFixed(1) + "°F"; }
                });
            }
            if (parsedHum.length > 0) {
                hoverSets.push({
                    data: parsedHum, yScale: yHum, label: "Humidity",
                    color: "var(--accent-cyan)",
                    format: function (v) { return v.toFixed(0) + "%"; }
                });
            }
            hover.update(hoverSets);
        }
    }

    return { update: update };
};
