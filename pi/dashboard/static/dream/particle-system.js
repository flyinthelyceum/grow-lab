/**
 * Particle System — GPU-driven point sprite particles
 *
 * Creates a BufferGeometry-based particle system with:
 *  - Configurable particle count (default 50K, auto-downscale)
 *  - Per-particle: position, velocity, color, life, size
 *  - CPU update loop (WebGPU compute upgrade path in Phase B)
 *  - Additive blending with soft circle texture
 *  - Lifecycle: spawn, drift, fade, respawn
 *
 * The flow field drives particle velocities; sensor data modulates
 * color, density, spawn rate, and turbulence.
 */

import { THREE } from "./dream-core.js";

// Soft circle texture (generated at init, no external asset)
function createSoftCircleTexture(size) {
    var canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    var ctx = canvas.getContext("2d");
    var center = size / 2;
    var gradient = ctx.createRadialGradient(center, center, 0, center, center, center);
    gradient.addColorStop(0, "rgba(255,255,255,1.0)");
    gradient.addColorStop(0.3, "rgba(255,255,255,0.6)");
    gradient.addColorStop(0.7, "rgba(255,255,255,0.15)");
    gradient.addColorStop(1, "rgba(255,255,255,0.0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    var tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    return tex;
}

// Detect rough GPU capability and pick particle count
function detectParticleCount(requested) {
    var gl = document.createElement("canvas").getContext("webgl2") ||
             document.createElement("canvas").getContext("webgl");
    if (!gl) return Math.min(requested, 5000);
    var ext = gl.getExtension("WEBGL_debug_renderer_info");
    if (ext) {
        var rendererStr = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) || "";
        // Integrated / mobile GPUs get fewer particles
        if (/Intel|Mali|Adreno|Apple GPU/i.test(rendererStr) &&
            !/Apple M[2-9]/i.test(rendererStr)) {
            return Math.min(requested, 20000);
        }
    }
    return requested;
}

function createParticleSystem(scene, options) {
    var opts = options || {};
    var requestedCount = opts.count || 50000;
    var count = detectParticleCount(requestedCount);
    var spreadRadius = opts.spreadRadius || 200;

    // Buffers
    var positions = new Float32Array(count * 3);
    var velocities = new Float32Array(count * 3);
    var colors = new Float32Array(count * 3);
    var sizes = new Float32Array(count);
    var lives = new Float32Array(count);
    var maxLives = new Float32Array(count);
    var alphas = new Float32Array(count);

    // Initialize particles in a sphere
    for (var i = 0; i < count; i++) {
        respawnParticle(i);
    }

    function respawnParticle(idx) {
        // Random position on sphere surface, then scatter inward
        var theta = Math.random() * Math.PI * 2;
        var phi = Math.acos(2 * Math.random() - 1);
        var r = spreadRadius * (0.1 + Math.random() * 0.9);
        var i3 = idx * 3;
        positions[i3] = r * Math.sin(phi) * Math.cos(theta);
        positions[i3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        positions[i3 + 2] = r * Math.cos(phi);

        velocities[i3] = (Math.random() - 0.5) * 0.3;
        velocities[i3 + 1] = (Math.random() - 0.5) * 0.3;
        velocities[i3 + 2] = (Math.random() - 0.5) * 0.3;

        // Default cool teal — overridden by flow field
        colors[i3] = 0.15;
        colors[i3 + 1] = 0.5;
        colors[i3 + 2] = 0.65;

        sizes[idx] = 1.0 + Math.random() * 2.5;
        var life = 3000 + Math.random() * 8000; // 3-11 seconds
        maxLives[idx] = life;
        lives[idx] = life;
        alphas[idx] = 0;
    }

    // Geometry
    var geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("customColor", new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1));
    geometry.setAttribute("alpha", new THREE.BufferAttribute(alphas, 1));

    // Shader material
    var material = new THREE.ShaderMaterial({
        uniforms: {
            uTexture: { value: createSoftCircleTexture(64) },
            uPixelRatio: { value: Math.min(window.devicePixelRatio || 1, 2) },
        },
        vertexShader: [
            "attribute vec3 customColor;",
            "attribute float size;",
            "attribute float alpha;",
            "varying vec3 vColor;",
            "varying float vAlpha;",
            "uniform float uPixelRatio;",
            "void main() {",
            "    vColor = customColor;",
            "    vAlpha = alpha;",
            "    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);",
            "    gl_PointSize = size * uPixelRatio * (200.0 / -mvPosition.z);",
            "    gl_PointSize = clamp(gl_PointSize, 0.5, 40.0);",
            "    gl_Position = projectionMatrix * mvPosition;",
            "}"
        ].join("\n"),
        fragmentShader: [
            "uniform sampler2D uTexture;",
            "varying vec3 vColor;",
            "varying float vAlpha;",
            "void main() {",
            "    vec4 texel = texture2D(uTexture, gl_PointCoord);",
            "    if (texel.a < 0.01) discard;",
            "    gl_FragColor = vec4(vColor * texel.rgb, texel.a * vAlpha);",
            "}"
        ].join("\n"),
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
    });

    var points = new THREE.Points(geometry, material);
    scene.add(points);

    // Burst state
    var bursts = [];

    // Update params (set by flow field / sensor mapping)
    var params = {
        baseColor: new THREE.Vector3(0.15, 0.5, 0.65),   // teal
        colorVariance: 0.15,
        speedMultiplier: 1.0,
        spawnRate: 1.0,        // 0-2, controls how quickly dead particles respawn
        turbulence: 0.5,       // curl noise amplitude
        globalAlpha: 1.0,
    };

    function update(dt, flowField) {
        var dtSec = dt / 1000;
        var posAttr = geometry.attributes.position;
        var colAttr = geometry.attributes.customColor;
        var sizeAttr = geometry.attributes.size;
        var alphaAttr = geometry.attributes.alpha;

        for (var i = 0; i < count; i++) {
            lives[i] -= dt;

            // Respawn dead particles
            if (lives[i] <= 0) {
                if (Math.random() < params.spawnRate) {
                    respawnParticle(i);
                    // Apply current base color with variance
                    var i3 = i * 3;
                    colors[i3] = params.baseColor.x + (Math.random() - 0.5) * params.colorVariance;
                    colors[i3 + 1] = params.baseColor.y + (Math.random() - 0.5) * params.colorVariance;
                    colors[i3 + 2] = params.baseColor.z + (Math.random() - 0.5) * params.colorVariance;
                } else {
                    alphas[i] = 0;
                }
                continue;
            }

            var i3 = i * 3;
            var x = positions[i3];
            var y = positions[i3 + 1];
            var z = positions[i3 + 2];

            // Flow field force
            if (flowField) {
                var force = flowField.sample(x, y, z);
                velocities[i3] += force.x * params.turbulence * dtSec;
                velocities[i3 + 1] += force.y * params.turbulence * dtSec;
                velocities[i3 + 2] += force.z * params.turbulence * dtSec;
            }

            // Damping
            var damping = 0.998;
            velocities[i3] *= damping;
            velocities[i3 + 1] *= damping;
            velocities[i3 + 2] *= damping;

            // Position integration
            var speed = params.speedMultiplier;
            positions[i3] += velocities[i3] * speed * dtSec * 60;
            positions[i3 + 1] += velocities[i3 + 1] * speed * dtSec * 60;
            positions[i3 + 2] += velocities[i3 + 2] * speed * dtSec * 60;

            // Lifecycle alpha: fade in first 10%, fade out last 20%
            var lifeRatio = lives[i] / maxLives[i];
            var fadeIn = Math.min(1, (1 - lifeRatio) / 0.1);
            var fadeOut = Math.min(1, lifeRatio / 0.2);
            alphas[i] = fadeIn * fadeOut * params.globalAlpha;

            // Respawn if too far from center
            var dist = Math.sqrt(x * x + y * y + z * z);
            if (dist > spreadRadius * 2.5) {
                lives[i] = 0;
            }
        }

        // Process bursts
        for (var b = bursts.length - 1; b >= 0; b--) {
            var burst = bursts[b];
            burst.age += dt;
            if (burst.age > burst.duration) {
                bursts.splice(b, 1);
            }
        }

        // Mark buffers dirty
        posAttr.needsUpdate = true;
        colAttr.needsUpdate = true;
        alphaAttr.needsUpdate = true;
    }

    function triggerBurst(burstColor, burstCount) {
        var bc = burstCount || 2000;
        var col = burstColor || new THREE.Vector3(0, 0.85, 0.95); // cyan
        var spawned = 0;

        for (var i = 0; i < count && spawned < bc; i++) {
            if (lives[i] <= 0 || lives[i] / maxLives[i] < 0.15) {
                var i3 = i * 3;
                // Spawn near center
                positions[i3] = (Math.random() - 0.5) * 10;
                positions[i3 + 1] = (Math.random() - 0.5) * 10;
                positions[i3 + 2] = (Math.random() - 0.5) * 10;

                // Fast outward velocity
                var theta = Math.random() * Math.PI * 2;
                var phi = Math.acos(2 * Math.random() - 1);
                var speed = 1.5 + Math.random() * 2.5;
                velocities[i3] = Math.sin(phi) * Math.cos(theta) * speed;
                velocities[i3 + 1] = Math.sin(phi) * Math.sin(theta) * speed;
                velocities[i3 + 2] = Math.cos(phi) * speed;

                colors[i3] = col.x;
                colors[i3 + 1] = col.y;
                colors[i3 + 2] = col.z;

                sizes[i] = 2.0 + Math.random() * 3.0;
                maxLives[i] = 1500 + Math.random() * 1500; // 1.5-3s
                lives[i] = maxLives[i];
                alphas[i] = 0;
                spawned++;
            }
        }

        bursts.push({ age: 0, duration: 3000 });
    }

    return {
        mesh: points,
        params: params,
        update: update,
        triggerBurst: triggerBurst,
        getCount: function () { return count; },
        getActiveCount: function () {
            var active = 0;
            for (var i = 0; i < count; i++) {
                if (lives[i] > 0 && alphas[i] > 0.01) active++;
            }
            return active;
        },
    };
}

export { createParticleSystem };
