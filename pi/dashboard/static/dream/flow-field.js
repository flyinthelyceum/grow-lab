/**
 * Flow Field — 3D curl noise vector field
 *
 * Generates a divergence-free velocity field using the curl of 3D simplex
 * noise. Sensor data modulates field parameters: scale, speed, curl
 * strength, turbulence amplitude.
 *
 * Simplex noise implementation adapted from Stefan Gustavson's classic
 * public-domain reference (simplified for this use case).
 */

// -------------------------------------------------------
// 3D Simplex noise (compact implementation)
// -------------------------------------------------------

var grad3 = [
    [1,1,0],[-1,1,0],[1,-1,0],[-1,-1,0],
    [1,0,1],[-1,0,1],[1,0,-1],[-1,0,-1],
    [0,1,1],[0,-1,1],[0,1,-1],[0,-1,-1],
];

var perm = new Uint8Array(512);
var permMod12 = new Uint8Array(512);

(function initPerm() {
    var p = [];
    for (var i = 0; i < 256; i++) p[i] = i;
    // Deterministic shuffle (seed = 42)
    var seed = 42;
    for (var i = 255; i > 0; i--) {
        seed = (seed * 16807 + 0) % 2147483647;
        var j = seed % (i + 1);
        var tmp = p[i];
        p[i] = p[j];
        p[j] = tmp;
    }
    for (var i = 0; i < 512; i++) {
        perm[i] = p[i & 255];
        permMod12[i] = perm[i] % 12;
    }
})();

var F3 = 1.0 / 3.0;
var G3 = 1.0 / 6.0;

function noise3(x, y, z) {
    var s = (x + y + z) * F3;
    var i = Math.floor(x + s);
    var j = Math.floor(y + s);
    var k = Math.floor(z + s);
    var t = (i + j + k) * G3;
    var X0 = i - t, Y0 = j - t, Z0 = k - t;
    var x0 = x - X0, y0 = y - Y0, z0 = z - Z0;

    var i1, j1, k1, i2, j2, k2;
    if (x0 >= y0) {
        if (y0 >= z0) { i1=1; j1=0; k1=0; i2=1; j2=1; k2=0; }
        else if (x0 >= z0) { i1=1; j1=0; k1=0; i2=1; j2=0; k2=1; }
        else { i1=0; j1=0; k1=1; i2=1; j2=0; k2=1; }
    } else {
        if (y0 < z0) { i1=0; j1=0; k1=1; i2=0; j2=1; k2=1; }
        else if (x0 < z0) { i1=0; j1=1; k1=0; i2=0; j2=1; k2=1; }
        else { i1=0; j1=1; k1=0; i2=1; j2=1; k2=0; }
    }

    var x1 = x0 - i1 + G3, y1 = y0 - j1 + G3, z1 = z0 - k1 + G3;
    var x2 = x0 - i2 + 2*G3, y2 = y0 - j2 + 2*G3, z2 = z0 - k2 + 2*G3;
    var x3 = x0 - 1 + 3*G3, y3 = y0 - 1 + 3*G3, z3 = z0 - 1 + 3*G3;

    var ii = i & 255, jj = j & 255, kk = k & 255;

    var n0 = 0, n1 = 0, n2 = 0, n3 = 0;

    var t0 = 0.6 - x0*x0 - y0*y0 - z0*z0;
    if (t0 > 0) {
        t0 *= t0;
        var gi0 = permMod12[ii + perm[jj + perm[kk]]];
        n0 = t0 * t0 * (grad3[gi0][0]*x0 + grad3[gi0][1]*y0 + grad3[gi0][2]*z0);
    }
    var t1 = 0.6 - x1*x1 - y1*y1 - z1*z1;
    if (t1 > 0) {
        t1 *= t1;
        var gi1 = permMod12[ii+i1 + perm[jj+j1 + perm[kk+k1]]];
        n1 = t1 * t1 * (grad3[gi1][0]*x1 + grad3[gi1][1]*y1 + grad3[gi1][2]*z1);
    }
    var t2 = 0.6 - x2*x2 - y2*y2 - z2*z2;
    if (t2 > 0) {
        t2 *= t2;
        var gi2 = permMod12[ii+i2 + perm[jj+j2 + perm[kk+k2]]];
        n2 = t2 * t2 * (grad3[gi2][0]*x2 + grad3[gi2][1]*y2 + grad3[gi2][2]*z2);
    }
    var t3 = 0.6 - x3*x3 - y3*y3 - z3*z3;
    if (t3 > 0) {
        t3 *= t3;
        var gi3 = permMod12[ii+1 + perm[jj+1 + perm[kk+1]]];
        n3 = t3 * t3 * (grad3[gi3][0]*x3 + grad3[gi3][1]*y3 + grad3[gi3][2]*z3);
    }

    return 32 * (n0 + n1 + n2 + n3);
}

// -------------------------------------------------------
// Curl noise (divergence-free field from noise derivatives)
// -------------------------------------------------------

var EPSILON = 0.0001;

function curlNoise(x, y, z, scale, timeOffset) {
    var sx = x * scale + timeOffset;
    var sy = y * scale + timeOffset * 0.7;
    var sz = z * scale + timeOffset * 0.5;

    // Approximate partial derivatives via central differences
    var dnx_dy = (noise3(sx, sy + EPSILON, sz) - noise3(sx, sy - EPSILON, sz)) / (2 * EPSILON);
    var dnx_dz = (noise3(sx, sy, sz + EPSILON) - noise3(sx, sy, sz - EPSILON)) / (2 * EPSILON);

    // Use offset noise fields for the other two components
    var dny_dx = (noise3(sx + EPSILON, sy + 31.416, sz) - noise3(sx - EPSILON, sy + 31.416, sz)) / (2 * EPSILON);
    var dny_dz = (noise3(sx, sy + 31.416, sz + EPSILON) - noise3(sx, sy + 31.416, sz - EPSILON)) / (2 * EPSILON);

    var dnz_dx = (noise3(sx + EPSILON, sy, sz + 71.628) - noise3(sx - EPSILON, sy, sz + 71.628)) / (2 * EPSILON);
    var dnz_dy = (noise3(sx, sy + EPSILON, sz + 71.628) - noise3(sx, sy - EPSILON, sz + 71.628)) / (2 * EPSILON);

    return {
        x: dnx_dy - dny_dz,  // actually dn_z/dy - dn_y/dz
        y: dnz_dx - dnx_dz,
        z: dny_dx - dnz_dy,
    };
}

// -------------------------------------------------------
// Flow field module
// -------------------------------------------------------

function createFlowField() {
    var time = 0;
    var scale = 0.008;           // noise spatial frequency
    var speed = 0.0003;          // time evolution speed (units/ms)
    var amplitude = 2.0;         // force multiplier
    var turbulenceOctaves = 2;   // additional noise layers

    // Sensor-driven parameter targets (smoothed)
    var targetScale = scale;
    var targetSpeed = speed;
    var targetAmplitude = amplitude;

    function sample(x, y, z) {
        var curl = curlNoise(x, y, z, scale, time);

        // Add turbulence octave
        if (turbulenceOctaves >= 2) {
            var c2 = curlNoise(x, y, z, scale * 2.3, time * 1.5);
            curl.x += c2.x * 0.4;
            curl.y += c2.y * 0.4;
            curl.z += c2.z * 0.4;
        }

        return {
            x: curl.x * amplitude,
            y: curl.y * amplitude,
            z: curl.z * amplitude,
        };
    }

    function update(dt) {
        time += speed * dt;

        // Smooth parameter transitions
        scale += (targetScale - scale) * 0.02;
        speed += (targetSpeed - speed) * 0.02;
        amplitude += (targetAmplitude - amplitude) * 0.02;
    }

    return {
        sample: sample,
        update: update,

        // Sensor mapping methods
        applyTemperature: function (tempF) {
            // Higher temp = larger noise scale (more macro movement)
            var t = Math.max(0, Math.min(1, (tempF - 58) / 30));
            targetScale = 0.005 + t * 0.008;
        },

        applyHumidity: function (humPct) {
            // Higher humidity = slower, denser movement
            var h = Math.max(0, Math.min(1, (humPct - 20) / 70));
            targetSpeed = 0.0001 + (1 - h) * 0.0004;
        },

        applyPressure: function (hpa) {
            // Lower pressure = more amplitude (stormier)
            var p = Math.max(0, Math.min(1, (hpa - 990) / 40));
            targetAmplitude = 3.5 - p * 2.0;
        },

        getScale: function () { return scale; },
        getSpeed: function () { return speed; },
        getAmplitude: function () { return amplitude; },
    };
}

export { createFlowField, noise3 };
