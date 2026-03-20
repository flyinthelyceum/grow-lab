/**
 * Dream Core — Three.js scene, camera, bloom, and animation loop
 *
 * Sets up a WebGLRenderer (WebGPU upgrade path planned), perspective camera
 * with slow auto-orbit, UnrealBloomPass for Anadol-style glow, and a 60fps
 * animation loop with Visibility API pause.
 *
 * Exports to window.GrowLab.DreamMode namespace.
 */

import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";

window.GrowLab = window.GrowLab || {};
window.GrowLab.DreamMode = window.GrowLab.DreamMode || {};

// -------------------------------------------------------
// Temperature color scale (shared with art-core)
// -------------------------------------------------------

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

function tempToVec3(tempF) {
    var c = tempToRGB(tempF);
    return new THREE.Vector3(c.r / 255, c.g / 255, c.b / 255);
}

function cToF(c) {
    return c * 9 / 5 + 32;
}

// -------------------------------------------------------
// Scene setup
// -------------------------------------------------------

function createDreamScene(canvas) {
    var width = window.innerWidth;
    var height = window.innerHeight;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);

    // Renderer
    var renderer = new THREE.WebGLRenderer({
        canvas: canvas,
        antialias: false,
        alpha: false,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(dpr);
    renderer.setClearColor(0x000000, 1);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;

    // Scene
    var scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x000000, 0.0008);

    // Camera
    var camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 5000);
    camera.position.set(0, 0, 300);

    // Bloom
    var renderPass = new RenderPass(scene, camera);
    var bloomPass = new UnrealBloomPass(
        new THREE.Vector2(width, height),
        1.2,   // strength
        0.6,   // radius
        0.15   // threshold
    );
    var composer = new EffectComposer(renderer);
    composer.addPass(renderPass);
    composer.addPass(bloomPass);

    // Resize handler
    function onResize() {
        width = window.innerWidth;
        height = window.innerHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
        composer.setSize(width, height);
        bloomPass.resolution.set(width, height);
    }
    window.addEventListener("resize", onResize);

    return {
        renderer: renderer,
        scene: scene,
        camera: camera,
        composer: composer,
        bloomPass: bloomPass,
        getWidth: function () { return width; },
        getHeight: function () { return height; },
    };
}

// -------------------------------------------------------
// Camera orbit
// -------------------------------------------------------

function createOrbitController(camera) {
    var angle = 0;
    var radius = 300;
    var yOffset = 0;
    var speed = 0.00008; // radians per ms — very slow
    var targetRadius = 300;
    var targetY = 0;

    return {
        update: function (dt) {
            angle += speed * dt;
            radius += (targetRadius - radius) * 0.02;
            yOffset += (targetY - yOffset) * 0.02;
            camera.position.x = Math.sin(angle) * radius;
            camera.position.z = Math.cos(angle) * radius;
            camera.position.y = yOffset;
            camera.lookAt(0, 0, 0);
        },
        setRadius: function (r) { targetRadius = r; },
        setY: function (y) { targetY = y; },
        getAngle: function () { return angle; },
    };
}

// -------------------------------------------------------
// Animation loop (60fps, Visibility API pause)
// -------------------------------------------------------

function createAnimationLoop(composer) {
    var callbacks = [];
    var running = false;
    var lastTime = 0;
    var rafId = null;
    var frameCount = 0;
    var fpsAccum = 0;
    var fps = 60;

    function tick(now) {
        if (!running) return;
        rafId = requestAnimationFrame(tick);

        var delta = now - lastTime;
        if (delta < 1) return; // skip duplicate frames
        lastTime = now;

        var dt = Math.min(delta, 50); // cap at 50ms (20fps minimum)

        // FPS tracking
        frameCount++;
        fpsAccum += delta;
        if (fpsAccum >= 1000) {
            fps = Math.round(frameCount * 1000 / fpsAccum);
            frameCount = 0;
            fpsAccum = 0;
        }

        for (var i = 0; i < callbacks.length; i++) {
            callbacks[i](dt, now);
        }

        composer.render();
    }

    function resume() {
        if (running) return;
        running = true;
        lastTime = performance.now();
        rafId = requestAnimationFrame(tick);
    }

    function pause() {
        running = false;
        if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    }

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            pause();
        } else {
            resume();
        }
    });

    return {
        register: function (cb) {
            callbacks.push(cb);
            if (!running) resume();
        },
        pause: pause,
        resume: resume,
        isRunning: function () { return running; },
        getFps: function () { return fps; },
    };
}

// -------------------------------------------------------
// Exports
// -------------------------------------------------------

window.GrowLab.DreamMode.THREE = THREE;
window.GrowLab.DreamMode.createDreamScene = createDreamScene;
window.GrowLab.DreamMode.createOrbitController = createOrbitController;
window.GrowLab.DreamMode.createAnimationLoop = createAnimationLoop;
window.GrowLab.DreamMode.tempToRGB = tempToRGB;
window.GrowLab.DreamMode.tempToVec3 = tempToVec3;
window.GrowLab.DreamMode.cToF = cToF;

export {
    THREE,
    createDreamScene,
    createOrbitController,
    createAnimationLoop,
    tempToRGB,
    tempToVec3,
    cToF,
};
