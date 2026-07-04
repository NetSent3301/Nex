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
}

interface Ring {
  radius: number;
  tilt: number;
  rotation: number;
  speed: number;
  color: string;
  opacity: number;
  width: number;
}

interface Arc {
  pts: { x: number; y: number }[];
  progress: number;
  speed: number;
  color: string;
  width: number;
}

const PALE_VIOLET = "rgba(192,132,252,";
const VIOLET = "rgba(168,85,247,";
const DEEP_VIOLET = "rgba(124,58,237,";
const MAGENTA = "rgba(147,51,234,";

export class PlasmaCore {
  private cv: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private particles: Particle[] = [];
  private rings: Ring[] = [];
  private arcs: Arc[] = [];
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

  constructor(canvas: HTMLCanvasElement) {
    this.cv = canvas;
    this.ctx = canvas.getContext("2d")!;
  }

  start() {
    this.resize();
    this.initParticles();
    this.initRings();
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
    for (let i = 0; i < 260; i++) {
      this.particles.push(this.spawnParticle());
    }
  }

  private spawnParticle(): Particle {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const baseR = this.R * (0.75 + Math.random() * 0.25);
    const colors = [PALE_VIOLET, VIOLET, DEEP_VIOLET, MAGENTA];
    return {
      theta,
      phi,
      baseR,
      r: baseR,
      size: 0.8 + Math.random() * 1.8,
      baseOpacity: 0.15 + Math.random() * 0.55,
      color: colors[Math.floor(Math.random() * colors.length)],
      driftTheta: (Math.random() - 0.5) * 0.4,
      driftPhi: (Math.random() - 0.5) * 0.25,
      wobbleAmp: 0.02 + Math.random() * 0.04,
      wobbleFreq: 0.3 + Math.random() * 0.7,
      wobblePhase: Math.random() * Math.PI * 2,
      escaping: false,
      escapeT: 0,
    };
  }

  // ── RINGS ──

  private initRings() {
    this.rings = [
      { radius: this.R * 0.90, tilt: 0.30, rotation: 0, speed: 0.35, color: VIOLET, opacity: 0.18, width: 1.0 },
      { radius: this.R * 0.78, tilt: -0.55, rotation: 0, speed: -0.45, color: PALE_VIOLET, opacity: 0.14, width: 0.8 },
      { radius: this.R * 1.00, tilt: 0.70, rotation: 0, speed: 0.20, color: DEEP_VIOLET, opacity: 0.12, width: 1.0 },
      { radius: this.R * 0.65, tilt: -0.25, rotation: 0, speed: -0.55, color: MAGENTA, opacity: 0.16, width: 0.7 },
      { radius: this.R * 0.95, tilt: 0.95, rotation: 0, speed: 0.15, color: VIOLET, opacity: 0.08, width: 0.6 },
      { radius: this.R * 0.52, tilt: 0.45, rotation: 0, speed: 0.65, color: PALE_VIOLET, opacity: 0.12, width: 0.6 },
    ];
  }

  // ── UPDATE ──

  private update(dt: number) {
    const breathe = 1 + Math.sin(this.time * 1.8) * 0.015;

    // Particles
    for (const p of this.particles) {
      if (p.escaping) {
        p.escapeT += dt * 0.5;
        if (p.escapeT >= 1) {
          Object.assign(p, this.spawnParticle());
          p.baseR = this.R * (0.75 + Math.random() * 0.25);
          continue;
        }
        const t = p.escapeT;
        p.r = p.baseR * (1 + t * t * 0.6);
        p.size = (0.8 + t * 1.2) * breathe;
        p.theta += p.driftTheta * dt * 3;
        p.phi += p.driftPhi * dt * 3;
        continue;
      }

      p.theta += p.driftTheta * dt;
      p.phi += p.driftPhi * dt;

      const wobble = Math.sin(this.time * p.wobbleFreq + p.wobblePhase) * p.wobbleAmp;
      const shellR = p.baseR * breathe;
      p.r = shellR * (1 + wobble);
    }

    // Escape trigger
    const escapeChance = 0.15 * dt;
    for (const p of this.particles) {
      if (!p.escaping && Math.random() < escapeChance) {
        p.escaping = true;
        p.escapeT = 0;
        if (this.particles.filter((x) => x.escaping).length > 4) break;
      }
    }

    // Rings
    for (const r of this.rings) {
      r.rotation += r.speed * dt;
      r.radius = r.radius; // remains proportional
    }

    // Arcs
    this.arcTimer += dt;
    if (this.arcTimer > 1.5 + Math.random() * 3) {
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
  }

  // ── ARCS ──

  private spawnArc() {
    const theta1 = Math.random() * Math.PI * 2;
    const phi1 = Math.acos(2 * Math.random() - 1);
    const theta2 = (theta1 + 0.4 + Math.random() * 1.2) % (Math.PI * 2);
    const phi2 = Math.acos(2 * Math.random() - 1);

    const n = 20 + Math.floor(Math.random() * 16);
    const pts: { x: number; y: number }[] = [];
    const colors = [VIOLET, PALE_VIOLET, DEEP_VIOLET, MAGENTA];

    for (let i = 0; i <= n; i++) {
      const t = i / n;
      const theta = theta1 + (theta2 - theta1) * t;
      const phi = phi1 + (phi2 - phi1) * t + Math.sin(t * Math.PI) * (Math.random() - 0.5) * 0.06;
      const rr = this.R * (0.98 + Math.random() * 0.04);
      const x = rr * Math.sin(phi) * Math.cos(theta);
      const y = rr * Math.sin(phi) * Math.sin(theta);
      const z = rr * Math.cos(phi);
      const perspective = 1 / (1 + z / (this.R * 2));
      pts.push({
        x: this.cx + x * perspective,
        y: this.cy - y * perspective,
      });
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

    // Nothing drawn outside the orbe bounding circle (soft clip)
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, this.R * 1.4, 0, Math.PI * 2);
    ctx.clip();

    const breathe = 1 + Math.sin(this.time * 1.8) * 0.015;
    const R = this.R * breathe;

    // ── Outer glow ──
    const glow = ctx.createRadialGradient(this.cx, this.cy, R * 0.2, this.cx, this.cy, R * 2);
    glow.addColorStop(0, "rgba(168,85,247,0.03)");
    glow.addColorStop(0.3, "rgba(168,85,247,0.025)");
    glow.addColorStop(0.6, "rgba(124,58,237,0.015)");
    glow.addColorStop(1, "transparent");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    // ── Core glow (breathing) ──
    const coreGlow = ctx.createRadialGradient(this.cx, this.cy, R * 0.05, this.cx, this.cy, R * 1.2);
    const gIntensity = 0.04 + Math.sin(this.time * 1.8) * 0.015;
    coreGlow.addColorStop(0, `rgba(168,85,247,${gIntensity * 0.8})`);
    coreGlow.addColorStop(0.5, `rgba(124,58,237,${gIntensity * 0.5})`);
    coreGlow.addColorStop(1, "transparent");
    ctx.fillStyle = coreGlow;
    ctx.fillRect(0, 0, w, h);

    // ── Back layer particles (z < 0, rendered behind core) ──
    const behind: Particle[] = [];
    const front: Particle[] = [];
    for (const p of this.particles) {
      const z = p.r * Math.cos(p.phi);
      if (z < 0) behind.push(p);
      else front.push(p);
    }

    const drawParticle = (p: Particle) => {
      const x = p.r * Math.sin(p.phi) * Math.cos(p.theta);
      const y = p.r * Math.sin(p.phi) * Math.sin(p.theta);
      const z = p.r * Math.cos(p.phi);
      const depth = 0.5 + (z / R + 1) / 2;
      const screenX = this.cx + x;
      const screenY = this.cy - y;
      const size = p.size * (0.5 + depth * 0.5);
      const alpha = p.baseOpacity * (0.4 + depth * 0.6);

      if (p.escaping) {
        const fade = Math.max(0, 1 - p.escapeT * 1.5);
        ctx.globalAlpha = fade * 0.6;
      } else {
        ctx.globalAlpha = alpha;
      }

      ctx.beginPath();
      ctx.arc(screenX, screenY, size, 0, Math.PI * 2);
      ctx.fillStyle = p.color + ctx.globalAlpha + ")";
      ctx.fill();

      // Small glow for brighter particles
      if (alpha > 0.4) {
        ctx.globalAlpha = alpha * 0.15;
        ctx.beginPath();
        ctx.arc(screenX, screenY, size * 3, 0, Math.PI * 2);
        ctx.fillStyle = p.color + ctx.globalAlpha + ")";
        ctx.fill();
      }
    };

    ctx.globalCompositeOperation = "source-over";

    // Draw behind particles
    for (const p of behind) drawParticle(p);

    // ── Semi-transparent dark core ──
    const core = ctx.createRadialGradient(this.cx, this.cy, 0, this.cx, this.cy, R * 0.55);
    core.addColorStop(0, "rgba(3, 2, 6, 0.92)");
    core.addColorStop(0.2, "rgba(5, 3, 10, 0.8)");
    core.addColorStop(0.5, "rgba(10, 6, 20, 0.4)");
    core.addColorStop(0.75, "rgba(20, 12, 35, 0.1)");
    core.addColorStop(1, "transparent");
    ctx.fillStyle = core;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, R * 0.55, 0, Math.PI * 2);
    ctx.fill();

    // ── Inner glow ring (energy horizon) ──
    const innerGlow = ctx.createRadialGradient(this.cx, this.cy, R * 0.3, this.cx, this.cy, R * 0.65);
    innerGlow.addColorStop(0, "transparent");
    innerGlow.addColorStop(0.7, "rgba(168,85,247,0.02)");
    innerGlow.addColorStop(0.85, "rgba(192,132,252,0.04)");
    innerGlow.addColorStop(1, "transparent");
    ctx.fillStyle = innerGlow;
    ctx.beginPath();
    ctx.arc(this.cx, this.cy, R * 0.65, 0, Math.PI * 2);
    ctx.fill();

    // ── Front particles (z >= 0) ──
    for (const p of front) drawParticle(p);

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
      ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);

      const softEdge = ctx.createRadialGradient(0, 0, rx * 0.92, 0, 0, rx);
      softEdge.addColorStop(0, "transparent");
      softEdge.addColorStop(0.7, ring.color + ring.opacity * 0.3 + ")");
      softEdge.addColorStop(0.9, ring.color + ring.opacity + ")");
      softEdge.addColorStop(1, "transparent");
      ctx.strokeStyle = softEdge;
      ctx.lineWidth = ring.width;
      ctx.stroke();
      ctx.restore();
    }

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
      ctx.moveTo(arc.pts[startIdx].x, arc.pts[startIdx].y);
      for (let i = startIdx + 1; i <= visLen; i++) {
        ctx.lineTo(arc.pts[i].x, arc.pts[i].y);
      }

      const arcFade = 1 - Math.abs(arc.progress - 0.5) * 1.5;
      const alpha = Math.max(0, arcFade) * 0.7;
      ctx.strokeStyle = arc.color + alpha + ")";
      ctx.lineWidth = arc.width * (0.5 + Math.sin(arc.progress * Math.PI) * 0.5);
      ctx.shadowColor = arc.color.slice(0, -1) + alpha * 1.2 + ")";
      ctx.shadowBlur = 12;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.restore();
    }

    // ── Final bloom overlay ──
    ctx.globalCompositeOperation = "screen";
    const bloom = ctx.createRadialGradient(this.cx, this.cy, R * 0.1, this.cx, this.cy, R * 1.1);
    const bloomIntensity = 0.03 + Math.sin(this.time * 1.8) * 0.012;
    bloom.addColorStop(0, "transparent");
    bloom.addColorStop(0.4, "transparent");
    bloom.addColorStop(0.8, `rgba(168,85,247,${bloomIntensity * 0.5})`);
    bloom.addColorStop(1, "transparent");
    ctx.fillStyle = bloom;
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";

    ctx.restore();
  }
}
