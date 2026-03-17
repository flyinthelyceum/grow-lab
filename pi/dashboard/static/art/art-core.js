/**
 * Art Core — Shared utilities for GROWLAB art visualizations
 *
 * Provides:
 *  - AnimationLoop: 30fps requestAnimationFrame with Visibility API pause
 *  - Color scales: temperature→color (3-zone gradient: blue→teal→amber)
 *  - DPI helper: set up canvas for retina displays
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    // -------------------------------------------------------
    // Animation Loop (30fps, pauses when tab hidden)
    // -------------------------------------------------------

    var FRAME_INTERVAL = 1000 / 30;
    var MAX_DELTA = FRAME_INTERVAL * 2;

    function AnimationLoop() {
        this._callbacks = [];
        this._running = false;
        this._lastTime = 0;
        this._rafId = null;
        this._tick = this._tick.bind(this);

        var self = this;
        document.addEventListener("visibilitychange", function () {
            if (document.hidden) {
                self.pause();
            } else {
                self.resume();
            }
        });
    }

    AnimationLoop.prototype.register = function (callback) {
        this._callbacks.push(callback);
        if (!this._running && this._callbacks.length > 0) {
            this.resume();
        }
    };

    AnimationLoop.prototype.unregister = function (callback) {
        this._callbacks = this._callbacks.filter(function (cb) { return cb !== callback; });
        if (this._callbacks.length === 0) {
            this.pause();
        }
    };

    AnimationLoop.prototype.resume = function () {
        if (this._running) return;
        this._running = true;
        this._lastTime = performance.now();
        this._rafId = requestAnimationFrame(this._tick);
    };

    AnimationLoop.prototype.pause = function () {
        this._running = false;
        if (this._rafId !== null) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }
    };

    AnimationLoop.prototype._tick = function (now) {
        if (!this._running) return;

        var delta = now - this._lastTime;

        if (delta >= FRAME_INTERVAL) {
            var dt = Math.min(delta, MAX_DELTA);
            this._lastTime = now - (delta % FRAME_INTERVAL);

            for (var i = 0; i < this._callbacks.length; i++) {
                this._callbacks[i](dt, now);
            }
        }

        this._rafId = requestAnimationFrame(this._tick);
    };

    // -------------------------------------------------------
    // DPI-aware canvas setup (uses window dimensions directly)
    // -------------------------------------------------------

    function setupCanvas(canvas) {
        var dpr = window.devicePixelRatio || 1;
        var w = window.innerWidth;
        var h = window.innerHeight;
        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + "px";
        canvas.style.height = h + "px";
        var ctx = canvas.getContext("2d");
        ctx.scale(dpr, dpr);
        return {
            ctx: ctx,
            width: w,
            height: h,
            dpr: dpr,
        };
    }

    // -------------------------------------------------------
    // Color scales — 3-zone temperature gradient (saturated)
    // -------------------------------------------------------

    // Temperature (°F) → RGB: deep slate blue → cool teal → warm amber
    // 58°F and below = coldest, 88°F and above = hottest
    function tempToRGB(tempF) {
        var t = Math.max(0, Math.min(1, (tempF - 58) / 30));
        var r, g, b;
        if (t < 0.35) {
            var s = t / 0.35;
            r = 40 + s * 20;
            g = 60 + s * 60;
            b = 120 + s * 40;
        } else if (t < 0.65) {
            var s = (t - 0.35) / 0.3;
            r = 60 + s * 130;
            g = 120 + s * 30;
            b = 160 - s * 80;
        } else {
            var s = (t - 0.65) / 0.35;
            r = 190 + s * 45;
            g = 150 + s * 20;
            b = 80 - s * 30;
        }
        return { r: Math.round(r), g: Math.round(g), b: Math.round(b) };
    }

    function temperatureColor(tempF) {
        var c = tempToRGB(tempF);
        return "rgb(" + c.r + "," + c.g + "," + c.b + ")";
    }

    function temperatureColorRGBA(tempF, alpha) {
        var c = tempToRGB(tempF);
        return "rgba(" + c.r + "," + c.g + "," + c.b + "," + alpha + ")";
    }

    // Humidity (%) → opacity: 20% → 0.05, 90% → 0.4
    function humidityOpacity(humPct) {
        return 0.05 + Math.max(0, Math.min(1, (humPct - 20) / 70)) * 0.35;
    }

    // °C → °F
    function cToF(c) {
        return c * 9 / 5 + 32;
    }

    // -------------------------------------------------------
    // Exports
    // -------------------------------------------------------

    window.GrowLab.ArtMode.AnimationLoop = AnimationLoop;
    window.GrowLab.ArtMode.setupCanvas = setupCanvas;
    window.GrowLab.ArtMode.tempToRGB = tempToRGB;
    window.GrowLab.ArtMode.temperatureColor = temperatureColor;
    window.GrowLab.ArtMode.temperatureColorRGBA = temperatureColorRGBA;
    window.GrowLab.ArtMode.humidityOpacity = humidityOpacity;
    window.GrowLab.ArtMode.cToF = cToF;

})();
