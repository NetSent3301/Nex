interface Particle {
  theta: number;
  phi: number;
  baseR: number;
  r: number;
  size: number;
  baseOpacity: number;
  color: string;
  driftTheta: number;
  driftPhi: number;
  wobbleAmp: number;
  wobbleFreq: number;
  wobblePhase: number;
  escaping: boolean;
  escapeT: number;
  trail: { x: number; y: number; z: number }[];
}

interface Ring {
  radius: number;
  tilt: number;
  rotation: number;
  speed: number;
  color: string;
  opacity: number;
  width: number;
  dash?: number;
}

interface Arc {
  pts: { x: number; y: number; z: number }[];
  progress: number;
  speed: number;
  color: string;
  width: number;
}

interface Wave {
  radius: number;
  maxRadius: number;
  opacity: number;
  speed: number;
}

interface Sparkle {
  theta: number;
  phi: number;
  dist: number;
  size: number;
  phase: number;
  speed: number;
  color: string;
}

const COLORS = [
  "rgba(192,132,252,",  // pale violet
  "rgba(168,85,247,",   // violet
  "rgba(124,58,237,",   // deep violet
  "rgba(147,51,234,",   // magenta
  "rgba(34,211,238,",   // cyan
  "rgba(99,102,241,",   // indigo
  "rgba(251,146,60,",   // warm amber
  "rgba(244,114,182,",  // coral pink
];

const PALE_VIOLET = COLORS[0];
const VIOLET = COLORS[1];
const DEEP_VIOLET = COLORS[2];
const MAGENTA = COLORS[3];
const CYAN = COLORS[4];
const INDIGO = COLORS[5];
const AMBER = COLORS[6];
const CORAL = COLORS[7];

export class PlasmaCore {
  private cv: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private rings: Ring[] = [];
  private arcs: Arc[] = [];
  private waves: Wave[] = [];
  private sparkles: Sparkle[] = [];
  private w = 0;
  private h = 0;
  private cx = 0;
  private cy = 0;
  private R = 0;
  private time = 0;
  private lastTs = 0;
  private animId = 0;
  private running = false;
  private arcTimer = 0;
  private waveTimer = 0;
  private targetMx = 0;
  private targetMy = 0;
  private mx = 0;
  private my = 0;
  private mouseIn = false;
  private globalRot = 0;

  constructor(canvas: HTMLCanvasElement) {
    this.cv = canvas;
    this.ctx = canvas.getContext("2d")!;
    this.bindMouse();
    this.bindResize();
  }

  private bindMouse() {
    this.cv.addEventListener("mousemove", (e) => {
      const rect = this.cv.getBoundingClientRect();
      this.targetMx = (e.clientX - rect.left) / rect.width;
      this.targetMy = (e.clientY - rect.top) / rect.height;
      this.mouseIn = true;
    });
    this.cv.addEventListener("mouseleave", () => {
      this.mouseIn = false;
    });
  }

  private bindResize() {
    window.addEventListener("resize", () => this.resize());
  }

  start() {
    this.resize();
    this.initParticles();
    this.initRings();
    this.initSparkles();
    this.running = true;
    this.lastTs = performance.now();
    this.tick(this.lastTs);
  }

  stop() {
    this.running = false;
    cancelAnimationFrame(this.animId);
  }

  resize() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.cv.parentElement?.getBoundingClientRect() || { width: 230, height: 230 };
    this.w = rect.width;
    this.h = rect.height;
    this.cv.width = this.w * dpr;
    this.cv.height = this.h * dpr;
    this.cv.style.width = this.w + "px";
    this.cv.style.height = this.h + "px";
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.cx = this.w / 2;
    this.cy = this.h / 2;
    this.R = Math.min(this.w, this.h) * 0.42;
  }

  private tick = (now: number) => {
    if (!this.running) return;
    const dt = Math.min((now - this.lastTs) / 1000, 0.05);
    this.lastTs = now;
    this.time += dt;
    this.update(dt);
    this.render();
    this.animId = requestAnimationFrame(this.tick);
  };

  // ── PARTICLES ──

  private initParticles() {
    this.particles = [];
    for (let i = 0; i < 500; i++) {
      this.particles.push(this.spawnParticle());
    }
  }

  private spawnParticle(): Particle {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const baseR = this.R * (0.4 + Math.random() * 0.6);
    return {
      theta,
      phi,
      baseR,
      r: baseR,
      size: 0.4 + Math.random() * 2.2,
      baseOpacity: 0.08 + Math.random() * 0.65,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      driftTheta: (Math.random() - 0.5) * 0.6,
      driftPhi: (Math.random() - 0.5) * 0.4,
      wobbleAmp: 0.008 + Math.random() * 0.06,
      wobbleFreq: 0.15 + Math.random() * 0.9,
      wobblePhase: Math.random() * Math.PI * 2,
      escaping: false,
      escapeT: 0,
      trail: [],
    };
  }

  // ── SPARKLES ──

  private initSparkles() {
    this.sparkles = [];
    for (let i = 0; i < 40; i++) {
      this.sparkles.push(this.spawnSparkle());
    }
  }

  private spawnSparkle(): Sparkle {
    return {
      theta: Math.random() * Math.PI * 2,
      phi: Math.acos(2 * Math.random() - 1),
      dist: this.R * (0.6 + Math.random() * 1.8),
      size: 0.3 + Math.random() * 1.2,
      phase: Math.random() * Math.PI * 2,
      speed: 0.3 + Math.random() * 0.7,
      color: COLORS[Math.floor(Math.random() * 4)],
    };
  }

  // ── RINGS ──

  private initRings() {
    this.rings = [
      { radius: this.R * 0.92, tilt: 0.30, rotation: 0, speed: 0.35, color: VIOLET, opacity: 0.25, width: 1.2 },
      { radius: this.R * 0.80, tilt: -0.55, rotation: 0, speed: -0.45, color: PALE_VIOLET, opacity: 0.20, width: 0.9 },
      { radius: this.R * 1.02, tilt: 0.70, rotation: 0, speed: 0.20, color: DEEP_VIOLET, opacity: 0.18, width: 1.1 },
      { radius: this.R * 0.66, tilt: -0.25, rotation: 0, speed: -0.55, color: MAGENTA, opacity: 0.22, width: 0.8 },
      { radius: this.R * 0.96, tilt: 0.95, rotation: 0, speed: 0.15, color: CYAN, opacity: 0.12, width: 0.7 },
      { radius: this.R * 0.50, tilt: 0.45, rotation: 0, speed: 0.65, color: INDIGO, opacity: 0.18, width: 0.7 },
      { radius: this.R * 0.72, tilt: 0.85, rotation: 0, speed: -0.30, color: CORAL, opacity: 0.10, width: 0.5, dash: 6 },
      { radius: this.R * 1.10, tilt: 0.15, rotation: 0, speed: 0.12, color: AMBER, opacity: 0.06, width: 0.4 },
    ];
  }

  // ── 3D PROJECTION ──

  private project(x: number, y: number, z: number): { sx: number; sy: number; scale: number } {
    const persp = 1 / (1 + z / (this.R * 3));
    return {
      sx: this.cx + x * persp,
      sy: this.cy - y * persp,
      scale: persp,
    };
  }

  private sphericalToCartesian(r: number, theta: number, phi: number): { x: number; y: number; z: number } {
    const t = theta + this.globalRot;
    return {
      x: r * Math.sin(phi) * Math.cos(t),
      y: r * Math.sin(phi) * Math.sin(t),
      z: r * Math.cos(phi),
    };
  }

  // ── UPDATE ──

  private update(dt: number) {
    const breathe = 1 + Math.sin(this.time * 1.8) * 0.018;

    this.globalRot += dt * 0.06;

    // Smooth mouse
    this.mx += (this.targetMx - this.mx) * Math.min(1, dt * 8);
    this.my += (this.targetMy - this.my) * Math.min(1, dt * 8);

    let mx = 0, my = 0;
    if (this.mouseIn) {
      mx = (this.mx - 0.5) * 0.25;
      my = (this.my - 0.5) * 0.25;
    }

    // Particles
    for (const p of this.particles) {
      if (p.escaping) {
        p.escapeT += dt * 0.5;
        if (p.escapeT >= 1) {
          Object.assign(p, this.spawnParticle());
          continue;
        }
        const t = p.escapeT;
        p.r = p.baseR * (1 + t * t * 0.6);
        p.size = (0.8 + t * 1.2) * breathe;
        p.theta += p.driftTheta * dt * 3;
        p.phi += p.driftPhi * dt * 3;
        continue;
      }

      p.theta += (p.driftTheta + mx) * dt;
      p.phi += (p.driftPhi + my) * dt;

      const wobble = Math.sin(this.time * p.wobbleFreq + p.wobblePhase) * p.wobbleAmp;
      const shellR = p.baseR * breathe;
      p.r = shellR * (1 + wobble);

      // Trail in 3D
      const pos = this.sphericalToCartesian(p.r, p.theta, p.phi);
      p.trail.push({ x: pos.x, y: pos.y, z: pos.z });
      if (p.trail.length > 5) p.trail.shift();
    }

    // Escape trigger
    const escapeChance = 0.2 * dt;
    let escapingCount = 0;
    for (const p of this.particles) {
      if (p.escaping) escapingCount++;
    }
    for (const p of this.particles) {
      if (!p.escaping && Math.random() < escapeChance) {
        p.escaping = true;
        p.escapeT = 0;
        escapingCount++;
        if (escapingCount > 6) break;
      }
    }

    // Rings
    for (const r of this.rings) {
      r.rotation += r.speed * dt;
    }

    // Arcs
    this.arcTimer += dt;
    if (this.arcTimer > 0.8 + Math.random() * 2.5) {
      this.arcTimer = 0;
      this.spawnArc();
    }
    for (let i = this.arcs.length - 1; i >= 0; i--) {
      const a = this.arcs[i];
      a.progress += a.speed * dt;
      if (a.progress >= 1) {
        this.arcs.splice(i, 1);
      }
    }

    // Energy waves
    this.waveTimer += dt;
    if (this.waveTimer > 2.5 + Math.random() * 3) {
      this.waveTimer = 0;
      this.waves.push({
        radius: 0,
        maxRadius: this.R * (0.8 + Math.random() * 0.6),
        opacity: 0.3 + Math.random() * 0.25,
        speed: 1.0 + Math.random() * 0.8,
      });
    }
    for (let i = this.waves.length - 1; i >= 0; i--) {
      const w = this.waves[i];
      w.radius += w.speed * dt * this.R;
      w.opacity -= dt * 0.4;
      if (w.opacity <= 0 || w.radius > w.maxRadius) {
        this.waves.splice(i, 1);
      }
    }

    // Sparkles
    for (const s of this.sparkles) {
      s.theta += dt * s.speed * 0.3;
      s.phi += dt * s.speed * 0.1;
    }
  }

  // ── ARCS ──

  private spawnArc() {
    const theta1 = Math.random() * Math.PI * 2;
    const phi1 = Math.acos(2 * Math.random() - 1);
    const theta2 = (theta1 + 0.4 + Math.random() * 1.2) % (Math.PI * 2);
    const phi2 = Math.acos(2 * Math.random() - 1);

    const n = 20 + Math.floor(Math.random() * 16);
    const pts: { x: number; y: number; z: number }[] = [];
    const colors = [VIOLET, PALE_VIOLET, DEEP_VIOLET, MAGENTA, CORAL];

    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const theta = theta1 + (theta2 - theta1) * t;
      const phi = phi1 + (phi2 - phi1) * t + Math.sin(t * Math.PI) * (Math.random() - 0.5) * 0.06;
      const rr = this.R * (0.98 + Math.random() * 0.04);
      const pos = this.sphericalToCartesian(rr, theta, phi);
      pts.push({ x: pos.x, y: pos.y, z: pos.z });
    }

    this.arcs.push({
      pts,
      progress: 0,
      speed: 0.6 + Math.random() * 0.6,
      color: colors[Math.floor(Math.random() * colors.length)],
      width: 0.8 + Math.random() * 1.2,
    });
  }

  // ── RENDER ──

  private render() {
    const ctx = this.ctx;
    const w = this.w;
    const h = this.h;

    ctx.clearRect(0, 0, w, h);

    const breathe = 1 + Math.sin(this.time * 1.8) * 0.018;
    const R = this.R * breathe;

    // Soft clip around the orb area
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, R * 1.8, 0, Math.PI * 2);
    ctx.clip();

    // ── Deep background glow ──
    const bgGlow = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, R * 2.5);
    const bgPulse = 0.03 + Math.sin(this.time * 1.8) * 0.01;
    bgGlow.addColorStop(0, `rgba(168,85,247,${bgPulse * 0.3})`);
    bgGlow.addColorStop(0.4, `rgba(124,58,237,${bgPulse * 0.2})`);
    bgGlow.addColorStop(0.7, `rgba(99,102,241,${bgPulse * 0.1})`);
    bgGlow.addColorStop(1, "transparent");
    ctx.fillStyle = bgGlow;
    ctx.fillRect(0, 0, w, h);

    // ── Outer glow ──
    const glow = ctx.createRadialGradient(this.cx, this.cy, R * 0.2, this.cx, this.cy, R * 2.2);
    glow.addColorStop(0, "rgba(168,85,247,0.05)");
    glow.addColorStop(0.3, "rgba(168,85,247,0.035)");
    glow.addColorStop(0.6, "rgba(124,58,237,0.02)");
    glow.addColorStop(0.8, "rgba(99,102,241,0.01)");
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    // ── Core glow (breathing) ──
    const coreGlow = ctx.createRadialGradient(this.cx, this.cy, R * 0.05, this.cx, this.cy, R * 1.5);
    const gIntensity = 0.06 + Math.sin(this.time * 1.8) * 0.025;
    coreGlow.addColorStop(0, `rgba(147,51,234,${gIntensity * 0.9})`);
    coreGlow.addColorStop(0.3, `rgba(168,85,247,${gIntensity * 0.6})`);
    coreGlow.addColorStop(0.6, `rgba(124,58,237,${gIntensity * 0.3})`);
    coreGlow.addColorStop(1, "transparent");
    ctx.fillStyle = coreGlow;
    ctx.fillRect(0, 0, w, h);

    // ── Energy waves ──
    for (const wave of this.waves) {
      const wa = Math.max(0, wave.opacity);
      const grad = ctx.createRadialGradient(this.cx, this.cy, wave.radius * 0.85, this.cx, this.cy, wave.radius);
      grad.addColorStop(0, "transparent");
      grad.addColorStop(0.6, `rgba(168,85,247,${wa * 0.15})`);
      grad.addColorStop(0.8, `rgba(192,132,252,${wa * 0.35})`);
      grad.addColorStop(0.95, `rgba(251,146,60,${wa * 0.1})`);
      grad.addColorStop(1, "transparent");
      ctx.strokeStyle = grad;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(this.cx, this.cy, wave.radius, 0, Math.PI * 2);
      ctx.stroke();
    }

    // ── Prepare depth-sorted particles ──
    const sorted = [...this.particles].sort((a, b) => {
      const za = a.r * Math.cos(a.phi);
      const zb = b.r * Math.cos(b.phi);
      return za - zb;
    });

    // Split into back/mid/front for rendering layers
    ctx.globalCompositeOperation = "source-over";

    const drawParticle = (p: Particle) => {
      const pos = this.sphericalToCartesian(p.r, p.theta, p.phi);
      const depth = 0.5 + (pos.z / R + 1) / 2;
      const proj = this.project(pos.x, pos.y, pos.z);
      const size = p.size * (0.4 + depth * 0.6) * proj.scale;
      const alpha = p.baseOpacity * (0.3 + depth * 0.7);

      if (p.escaping) {
        const fade = Math.max(0, 1 - p.escapeT * 1.5);
        ctx.globalAlpha = fade * 0.6;
      } else {
        ctx.globalAlpha = alpha;
      }

      // Trail
      if (!p.escaping && p.trail.length > 1) {
        for (let i = 1; i < p.trail.length; i++) {
          const t = p.trail[i];
          const tp = this.project(t.x, t.y, t.z);
          const ta = (i / p.trail.length) * alpha * 0.1;
          ctx.globalAlpha = ta;
          ctx.beginPath();
          ctx.arc(tp.sx, tp.sy, size * 0.35, 0, Math.PI * 2);
          ctx.fillStyle = p.color + ta + ")";
          ctx.fill();
        }
      }

      ctx.globalAlpha = p.escaping
        ? Math.max(0, 1 - p.escapeT * 1.5) * 0.6
        : alpha;

      if (ctx.globalAlpha < 0.01) return;

      ctx.beginPath();
      ctx.arc(proj.sx, proj.sy, Math.max(0.5, size), 0, Math.PI * 2);
      ctx.fillStyle = p.color + ctx.globalAlpha + ")";
      ctx.fill();

      // Glow for brighter particles
      if (alpha > 0.3) {
        ctx.globalAlpha = alpha * 0.15;
        ctx.beginPath();
        ctx.arc(proj.sx, proj.sy, size * 3, 0, Math.PI * 2);
        ctx.fillStyle = p.color + ctx.globalAlpha + ")";
        ctx.fill();
      }
    };

    // Draw particles back to front
    for (const p of sorted) drawParticle(p);

    // ── Semi-transparent dark core ──
    ctx.globalAlpha = 1;
    const core = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, R * 0.6);
    core.addColorStop(0, "rgba(3, 2, 6, 0.94)");
    core.addColorStop(0.15, "rgba(5, 3, 10, 0.85)");
    core.addColorStop(0.4, "rgba(10, 6, 22, 0.5)");
    core.addColorStop(0.65, "rgba(20, 12, 38, 0.15)");
    core.addColorStop(1, "transparent");
    ctx.fillStyle = core;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, R * 0.6, 0, Math.PI * 2);
    ctx.fill();

    // ── Inner glow ring (energy horizon) ──
    const innerGlow = ctx.createRadialGradient(this.cx, this.cy, R * 0.25, this.cx, this.cy, R * 0.75);
    innerGlow.addColorStop(0, "transparent");
    innerGlow.addColorStop(0.5, "rgba(168,85,247,0.015)");
    innerGlow.addColorStop(0.7, "rgba(192,132,252,0.04)");
    innerGlow.addColorStop(0.85, `rgba(244,114,182,0.025)`);
    innerGlow.addColorStop(1, "transparent");
    ctx.fillStyle = innerGlow;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, R * 0.75, 0, Math.PI * 2);
    ctx.fill();

    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;

    // ── Plasma rings ──
    for (const ring of this.rings) {
      const rx = ring.radius * breathe;
      const ry = rx * Math.cos(ring.tilt);

      if (ry <= 0) continue;

      ctx.save();
      ctx.translate(this.cx, this.cy);
      ctx.rotate(ring.rotation);
      ctx.beginPath();

      if (ring.dash) {
        ctx.setLineDash([ring.dash, ring.dash * 0.6]);
      }

      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);

      const softEdge = ctx.createRadialGradient(0, 0, rx * 0.9, 0, 0, rx);
      softEdge.addColorStop(0, "transparent");
      softEdge.addColorStop(0.5, ring.color + ring.opacity * 0.2 + ")");
      softEdge.addColorStop(0.8, ring.color + ring.opacity * 0.9 + ")");
      softEdge.addColorStop(1, "transparent");
      ctx.strokeStyle = softEdge;
      ctx.lineWidth = ring.width;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();
    }

    // ── Sparkles ──
    for (const s of this.sparkles) {
      const pos = this.sphericalToCartesian(s.dist, s.theta, s.phi);
      const proj = this.project(pos.x, pos.y, pos.z);
      const twinkle = 0.3 + Math.sin(this.time * s.speed * 2 + s.phase) * 0.7;
      const sa = Math.max(0, twinkle * 0.5);
      ctx.globalAlpha = sa;
      ctx.beginPath();
      ctx.arc(proj.sx, proj.sy, s.size * (0.5 + twinkle * 0.5), 0, Math.PI * 2);
      ctx.fillStyle = s.color + sa + ")";
      ctx.fill();

      // Sparkle glow
      if (twinkle > 0.6) {
        ctx.globalAlpha = sa * 0.3;
        ctx.beginPath();
        ctx.arc(proj.sx, proj.sy, s.size * 3, 0, Math.PI * 2);
        ctx.fillStyle = s.color + ctx.globalAlpha + ")";
        ctx.fill();
      }
    }

    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";

    // ── Electrical arcs ──
    for (const arc of this.arcs) {
      const visLen = Math.min(Math.floor(arc.progress * arc.pts.length), arc.pts.length - 1);
      if (visLen < 2) continue;

      const head = arc.progress;
      const tail = Math.max(0, head - 0.3);
      const startIdx = Math.floor(tail * arc.pts.length);

      ctx.save();
      ctx.beginPath();

      const startP = this.project(arc.pts[startIdx].x, arc.pts[startIdx].y, arc.pts[startIdx].z);
      ctx.moveTo(startP.sx, startP.sy);
      for (let i = startIdx + 1; i <= visLen; i++) {
        const p = this.project(arc.pts[i].x, arc.pts[i].y, arc.pts[i].z);
        ctx.lineTo(p.sx, p.sy);
      }

      const arcFade = 1 - Math.abs(arc.progress - 0.5) * 1.5;
      const alpha = Math.max(0, arcFade) * 0.8;
      ctx.strokeStyle = arc.color + alpha + ")";
      ctx.lineWidth = arc.width * (0.5 + Math.sin(arc.progress * Math.PI) * 0.5);
      ctx.shadowColor = arc.color.slice(0, -1) + alpha * 1.5 + ")";
      ctx.shadowBlur = 18;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.restore();
    }

    // ── Final bloom overlay ──
    ctx.globalCompositeOperation = "screen";
    const bloom = ctx.createRadialGradient(this.cx, this.cy, R * 0.1, this.cx, this.cy, R * 1.3);
    const bloomIntensity = 0.05 + Math.sin(this.time * 1.8) * 0.018;
    bloom.addColorStop(0, "transparent");
    bloom.addColorStop(0.5, "transparent");
    bloom.addColorStop(0.75, `rgba(168,85,247,${bloomIntensity * 0.4})`);
    bloom.addColorStop(0.88, `rgba(99,102,241,${bloomIntensity * 0.3})`);
    bloom.addColorStop(0.95, `rgba(251,146,60,${bloomIntensity * 0.1})`);
    bloom.addColorStop(1, "transparent");
    ctx.fillStyle = bloom;
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";

    ctx.restore();
  }
}
