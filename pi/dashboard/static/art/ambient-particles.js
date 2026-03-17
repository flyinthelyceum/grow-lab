/**
 * Ambient Particles — drifting field particles for "living" feel
 *
 * 120 particles drift across the full canvas with sine-wave wobble
 * and breathing opacity. Creates the Anadol-inspired sense that
 * the visualization is alive — the negative space breathes.
 *
 * Particles have lifecycle fade-in/out and respawn when off-canvas.
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    function createAmbientParticles(ctx, getCx, getCy, getMaxRadius) {
        var particles = [];
        var PARTICLE_COUNT = 120;
        var animTime = 0;

        for (var i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(spawnParticle());
        }

        function spawnParticle() {
            var W = getCx() * 2;
            var H = getCy() * 2;
            return {
                x: (Math.random() - 0.5) * W * 0.9,
                y: (Math.random() - 0.5) * H * 0.9,
                vx: (Math.random() - 0.5) * 0.2,
                vy: (Math.random() - 0.5) * 0.2,
                size: 0.8 + Math.random() * 2,
                alpha: 0.04 + Math.random() * 0.12,
                phase: Math.random() * Math.PI * 2,
                speed: 0.3 + Math.random() * 0.7,
                life: Math.random(),
            };
        }

        function render(dt) {
            animTime += dt;
            var cx = getCx();
            var cy = getCy();

            ctx.save();
            ctx.translate(cx, cy);

            for (var i = 0; i < particles.length; i++) {
                var p = particles[i];

                // Gentle drift with sine-wave wobble
                p.x += p.vx * p.speed * (dt / 16);
                p.y += p.vy * p.speed * (dt / 16);
                p.x += Math.sin(animTime / 4000 + p.phase) * 0.05;
                p.y += Math.cos(animTime / 5000 + p.phase * 1.3) * 0.05;

                p.life += 0.0002 * (dt / 16);

                // Respawn if off canvas or life expired
                var halfW = cx;
                var halfH = cy;
                if (Math.abs(p.x) > halfW || Math.abs(p.y) > halfH || p.life > 1) {
                    particles[i] = spawnParticle();
                    continue;
                }

                // Breathing opacity with lifecycle fade
                var breathAlpha = p.alpha * (0.6 + 0.4 * Math.sin(animTime / 3000 + p.phase));
                var lifeFade = p.life < 0.1 ? p.life / 0.1 : (p.life > 0.8 ? (1 - p.life) / 0.2 : 1);
                var finalAlpha = breathAlpha * lifeFade;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(180,210,230," + finalAlpha + ")";
                ctx.fill();
            }

            ctx.restore();
        }

        return { render: render };
    }

    window.GrowLab.ArtMode.createAmbientParticles = createAmbientParticles;

})();
