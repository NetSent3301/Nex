export type OrbState =
  | "idle"
  | "listening"
  | "thinking"
  | "tool"
  | "speaking"
  | "success"
  | "error";

type RGB = [number, number, number];

export interface OrbOptions {
  mode?: "full" | "mini";
  /** Escuchar el bus global "nex:orb" (default true). */
  listenGlobal?: boolean;
  /** Maximo de particulas (default segun tamaño). */
  maxParticles?: number;
}

/* ─────────────────────────────  BUS GLOBAL  ───────────────────────────── */

export interface OrbEventDetail {
  type:
    | "typing"
    | "send"
    | "thinking"
    | "tool_start"
    | "tool_end"
    | "text"
    | "done"
    | "error"
    | "stop"
    | "idle";
  tool?: string;
  ok?: boolean;
  chars?: number;
}

export function emitOrb(
  type: OrbEventDetail["type"],
  extra: Omit<OrbEventDetail, "type"> = {},
): void {
  try {
    window.dispatchEvent(
      new CustomEvent<OrbEventDetail>("nex:orb", { detail: { type, ...extra } }),
    );
  } catch {
    /* sin window (tests) */
  }
}

/* ─────────────────────────────  MOODS  ───────────────────────────── */

interface Mood {
  spin: number; // rad/s de rotacion global
  turb: number; // turbulencia de la superficie
  breathe: number; // Hz de respiracion
  ringSpeed: number;
  core: number; // brillo del nucleo 0..1
  contract: number; // escala del radio
  arcRate: number; // rayos por segundo
  speak: number; // 0..1 deformacion tipo ecualizador
  trail: number; // 0..1 estela
  energy: number; // 0..1 intensidad general
  a: RGB;
  b: RGB;
  c: RGB; // color del nucleo
}

const VIOLET: RGB = [168, 85, 247];
const INDIGO: RGB = [99, 102, 241];
const PALE: RGB = [192, 132, 252];
const CYAN: RGB = [34, 211, 238];

const MOODS: Record<OrbState, Mood> = {
  idle: {
    spin: 0.18, turb: 0.05, breathe: 0.22, ringSpeed: 0.25, core: 0.35, contract: 1,
    arcRate: 0.15, speak: 0, trail: 0.25, energy: 0.3, a: VIOLET, b: INDIGO, c: PALE,
  },
  listening: {
    spin: 0.1, turb: 0.04, breathe: 0.6, ringSpeed: 0.4, core: 0.5, contract: 0.94,
    arcRate: 0.3, speak: 0, trail: 0.3, energy: 0.5, a: CYAN, b: VIOLET, c: [165, 243, 252],
  },
  thinking: {
    spin: 0.9, turb: 0.16, breathe: 1.1, ringSpeed: 1.6, core: 0.75, contract: 0.96,
    arcRate: 3, speak: 0, trail: 0.55, energy: 0.8, a: [124, 58, 237], b: [244, 114, 182], c: [233, 213, 255],
  },
  tool: {
    spin: 0.55, turb: 0.1, breathe: 0.8, ringSpeed: 2.6, core: 0.65, contract: 1,
    arcRate: 1.5, speak: 0, trail: 0.5, energy: 0.75, a: [251, 146, 60], b: VIOLET, c: [254, 215, 170],
  },
  speaking: {
    spin: 0.3, turb: 0.08, breathe: 0.5, ringSpeed: 0.7, core: 0.8, contract: 1.03,
    arcRate: 0.4, speak: 1, trail: 0.4, energy: 0.85, a: PALE, b: CYAN, c: [245, 235, 255],
  },
  success: {
    spin: 0.4, turb: 0.03, breathe: 0.4, ringSpeed: 0.8, core: 1, contract: 1.05,
    arcRate: 0, speak: 0, trail: 0.3, energy: 0.9, a: [52, 211, 153], b: CYAN, c: [209, 250, 229],
  },
  error: {
    spin: 0.2, turb: 0.3, breathe: 1.6, ringSpeed: 0.2, core: 0.9, contract: 0.92,
    arcRate: 4, speak: 0, trail: 0.2, energy: 1, a: [239, 68, 68], b: [251, 146, 60], c: [254, 202, 202],
  },
};

const TOOL_TINT: Record<string, RGB> = {
  shell: [251, 146, 60],
  fs: [34, 211, 238],
  web: [96, 165, 250],
  git: [52, 211, 153],
  code: [244, 114, 182],
  image: [250, 204, 21],
  generic: [192, 132, 252],
};

function toolKind(name: string): string {
  const n = name.toLowerCase();
  if (/run_command|terminal|shell|bash|exec/.test(n)) return "shell";
  if (/git/.test(n)) return "git";
  if (/web|search|fetch|http|url/.test(n)) return "web";
  if (/image|img|vision/.test(n)) return "image";
  if (/lsp|code|analy|symbol|lint/.test(n)) return "code";
  if (/file|read|write|edit|list|glob|grep|dir|path/.test(n)) return "fs";
  return "generic";
}

/* ─────────────────────────────  UTIL  ───────────────────────────── */

const TAU = Math.PI * 2;
const clamp = (v: number, a: number, b: number) => (v < a ? a : v > b ? b : v);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpRGB = (a: RGB, b: RGB, t: number): RGB => [
  lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t),
];
const rgba = (c: RGB, a: number) =>
  `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${clamp(a, 0, 1).toFixed(3)})`;

/** Ruido barato 4D-ish suave, rango aprox [-1, 1]. */
function noise(x: number, y: number, z: number, t: number): number {
  return (
    Math.sin(x * 3.1 + t * 1.3 + Math.sin(y * 2.7 + t * 0.9)) *
    Math.cos(z * 2.9 - t * 1.1 + Math.sin(x * 2.3 - t * 0.7)) *
    0.7 +
    Math.sin((x + y + z) * 4.3 + t * 1.9) * 0.3
  );
}

/* ─────────────────────────────  TIPOS INTERNOS  ───────────────────────────── */

interface Wave { t0: number; speed: number; width: number; amp: number; col: RGB }
interface Ripple { t0: number; life: number; amp: number; col: RGB }
interface Arc { pts: number[]; t0: number; life: number; col: RGB }

const BUCKET_MIX = 6;
const BUCKET_DEPTH = 4;
const BUCKETS = BUCKET_MIX * BUCKET_DEPTH;
const BANDS = 40;
const MAX_SPARKS = 160;

/* ─────────────────────────────  ENGINE  ───────────────────────────── */

export class OrbEngine {
  private cv: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;
  private opts: Required<OrbOptions>;
  private mini: boolean;

  // geometria
  private w = 0; private h = 0; private dpr = 1; private R = 0;
  private nx!: Float32Array; private ny!: Float32Array; private nz!: Float32Array;
  private pr0!: Float32Array; private psize!: Float32Array; private pmix!: Uint8Array;
  private pphase!: Float32Array;
  private N = 0;
  private px!: Float32Array; private py!: Float32Array; private prad!: Float32Array;
  private lists: Int32Array[] = [];
  private counts = new Int32Array(BUCKETS);

  // estado
  private mood: Mood = { ...MOODS.idle, a: [...MOODS.idle.a], b: [...MOODS.idle.b], c: [...MOODS.idle.c] };
  private sticky: OrbState = "idle";
  private transient: OrbState | null = null;
  private transientUntil = 0;
  private toolDepth = 0;
  private toolTint: RGB = TOOL_TINT.generic;
  private lastTextAt = 0;
  private time = 0;
  private yaw = 0; private pitch = 0;
  private yawT = 0; private pitchT = 0;
  private mx = 0.5; private my = 0.5; private mouseIn = false;
  private env = 0; private ext = 0; private flash = 0; private shake = 0;
  private bands = new Float32Array(BANDS);
  private ringPhase = [0, 1.7, 3.4];
  private waves: Wave[] = [];
  private ripples: Ripple[] = [];
  private arcs: Arc[] = [];
  private sx = new Float32Array(MAX_SPARKS); private sy = new Float32Array(MAX_SPARKS);
  private svx = new Float32Array(MAX_SPARKS); private svy = new Float32Array(MAX_SPARKS);
  private slife = new Float32Array(MAX_SPARKS); private scol: RGB[] = [];
  private sparkHead = 0;

  // ciclo de vida
  private raf = 0; private running = false; private enabled = true;
  private visible = true; private pageVisible = true;
  private lastTs = 0; private frameMs = 12; private quality = 1; private slowFrames = 0;
  private reduceMotion = false;
  private cleanups: Array<() => void> = [];

  constructor(canvas: HTMLCanvasElement, opts: OrbOptions = {}) {
    this.cv = canvas;
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("OrbEngine: canvas 2D no disponible");
    this.ctx = ctx;
    this.mini = opts.mode === "mini";
    this.opts = {
      mode: this.mini ? "mini" : "full",
      listenGlobal: opts.listenGlobal ?? true,
      maxParticles: opts.maxParticles ?? (this.mini ? 160 : 1100),
    };
    for (let i = 0; i < BUCKETS; i++) this.lists.push(new Int32Array(this.opts.maxParticles));
    for (let i = 0; i < MAX_SPARKS; i++) this.scol.push(VIOLET);

    this.buildParticles();
    this.bindEnv();
  }

  /* ───── API publica ───── */

  start(): void {
    if (this.running) return;
    this.running = true;
    this.resize();
    this.lastTs = performance.now();
    this.schedule();
  }

  stop(): void {
    this.running = false;
    cancelAnimationFrame(this.raf);
  }

  destroy(): void {
    this.stop();
    this.cleanups.forEach((fn) => fn());
    this.cleanups = [];
  }

  setEnabled(on: boolean): void {
    this.enabled = on;
    if (this.running) this.schedule();
  }

  /** `sticky` = estado base hasta que lo cambies; si no, dura `ms` y vuelve al base. */
  setState(state: OrbState, o: { sticky?: boolean; ms?: number } = {}): void {
    if (o.sticky) {
      this.sticky = state;
      this.transient = null;
    } else {
      this.transient = state;
      this.transientUntil = this.time + (o.ms ?? 1.2);
    }
    this.kick();
  }

  pulse(strength = 1, tint?: RGB): void {
    const s = clamp(strength, 0, 2);
    const col = tint ?? this.mood.b;
    this.waves.push({ t0: this.time, speed: 1.6 + s * 0.6, width: 0.28, amp: 0.1 + 0.12 * s, col });
    this.ripples.push({ t0: this.time, life: 0.9, amp: 0.25 + 0.3 * s, col });
    if (this.waves.length > 8) this.waves.shift();
    if (this.ripples.length > 8) this.ripples.shift();
    this.emitSparks(Math.round(6 + 10 * s), col);
    this.flash = Math.min(1, this.flash + 0.35 * s);
    this.env = Math.min(1.2, this.env + 0.25 * s);
    this.kick();
  }

  feedText(chars: number): void {
    this.env = Math.min(1.2, this.env + clamp(chars / 28, 0.08, 0.6));
    this.lastTextAt = this.time;
    this.sticky = "speaking";
    this.kick();
  }

  setExternalLevel(level: number): void {
    this.ext = clamp(level, 0, 1);
    this.kick();
  }

  /* ───── bus global ───── */

  private onBus = (e: Event): void => {
    const d = (e as CustomEvent<OrbEventDetail>).detail;
    if (!d) return;
    switch (d.type) {
      case "typing":
        if (this.sticky === "idle" || this.sticky === "success") {
          this.setState("listening", { ms: 1.6 });
        }
        this.pulse(0.15);
        break;
      case "send":
        this.toolDepth = 0;
        this.setState("thinking", { sticky: true });
        this.pulse(1);
        break;
      case "thinking":
        this.setState("thinking", { sticky: true });
        break;
      case "tool_start":
        this.toolDepth++;
        this.toolTint = TOOL_TINT[toolKind(d.tool ?? "")] ?? TOOL_TINT.generic;
        this.setState("tool", { sticky: true });
        this.pulse(0.8, this.toolTint);
        break;
      case "tool_end":
        this.toolDepth = Math.max(0, this.toolDepth - 1);
        this.pulse(d.ok === false ? 0.9 : 0.5, d.ok === false ? MOODS.error.a : this.toolTint);
        if (this.toolDepth === 0) this.setState("thinking", { sticky: true });
        break;
      case "text":
        this.feedText(d.chars ?? 12);
        break;
      case "done":
        this.toolDepth = 0;
        this.sticky = "idle";
        this.setState("success", { ms: 1.4 });
        this.pulse(1.5, MOODS.success.a);
        break;
      case "error":
        this.toolDepth = 0;
        this.sticky = "idle";
        this.shake = 1;
        this.setState("error", { ms: 2 });
        this.pulse(1.8, MOODS.error.a);
        break;
      case "stop":
      case "idle":
        this.toolDepth = 0;
        this.setState("idle", { sticky: true });
        break;
    }
  };

  /* ───── setup ───── */

  private bindEnv(): void {
    const on = <K extends keyof WindowEventMap>(t: K, fn: (e: WindowEventMap[K]) => void) => {
      window.addEventListener(t, fn);
      this.cleanups.push(() => window.removeEventListener(t, fn));
    };

    if (this.opts.listenGlobal) {
      window.addEventListener("nex:orb", this.onBus);
      this.cleanups.push(() => window.removeEventListener("nex:orb", this.onBus));
    }

    if (!this.mini) {
      const move = (e: MouseEvent) => {
        const r = this.cv.getBoundingClientRect();
        // parallax suave usando toda la ventana, no solo el canvas
        this.mx = clamp((e.clientX - r.left) / Math.max(1, r.width), -1, 2);
        this.my = clamp((e.clientY - r.top) / Math.max(1, r.height), -1, 2);
        this.mouseIn = true;
      };
      on("mousemove", move);
      on("mouseout", () => { this.mouseIn = false; });
      this.cv.addEventListener("click", () => this.pulse(1.2));
      on("resize", () => this.resize());
    }

    if (typeof ResizeObserver !== "undefined") {
      const ro = new ResizeObserver(() => this.resize());
      ro.observe(this.cv);
      this.cleanups.push(() => ro.disconnect());
    }
    if (typeof IntersectionObserver !== "undefined") {
      const io = new IntersectionObserver((en) => {
        this.visible = en.some((x) => x.isIntersecting);
        if (this.visible) this.kick();
      });
      io.observe(this.cv);
      this.cleanups.push(() => io.disconnect());
    }
    const vis = () => {
      this.pageVisible = !document.hidden;
      if (this.pageVisible) this.kick();
    };
    document.addEventListener("visibilitychange", vis);
    this.cleanups.push(() => document.removeEventListener("visibilitychange", vis));

    if (typeof matchMedia !== "undefined") {
      const mq = matchMedia("(prefers-reduced-motion: reduce)");
      this.reduceMotion = mq.matches;
      const h = () => { this.reduceMotion = mq.matches; this.kick(); };
      mq.addEventListener?.("change", h);
      this.cleanups.push(() => mq.removeEventListener?.("change", h));
    }
  }

  private buildParticles(): void {
    const N = this.opts.maxParticles;
    this.N = N;
    this.nx = new Float32Array(N); this.ny = new Float32Array(N); this.nz = new Float32Array(N);
    this.pr0 = new Float32Array(N); this.psize = new Float32Array(N);
    this.pmix = new Uint8Array(N); this.pphase = new Float32Array(N);
    this.px = new Float32Array(N); this.py = new Float32Array(N); this.prad = new Float32Array(N);
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2;
      const r = Math.sqrt(1 - y * y);
      const th = golden * i;
      this.nx[i] = Math.cos(th) * r; this.ny[i] = y; this.nz[i] = Math.sin(th) * r;
      const shell = Math.random();
      // 70% en la superficie, 30% en nebulosa interior
      this.pr0[i] = shell < 0.7 ? 0.9 + Math.random() * 0.12 : 0.35 + Math.random() * 0.5;
      this.psize[i] = 0.5 + Math.random() * 1.5;
      this.pmix[i] = Math.floor(Math.random() * BUCKET_MIX);
      this.pphase[i] = Math.random() * TAU;
    }
  }

  private resize(): void {
    const r = this.cv.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, Math.round(r.width));
    const h = Math.max(1, Math.round(r.height));
    this.dpr = dpr; this.w = w; this.h = h;
    this.cv.width = Math.round(w * dpr);
    this.cv.height = Math.round(h * dpr);
    this.R = Math.min(w, h) * (this.mini ? 0.3 : 0.25);
    this.kick();
  }

  /* ───── bucle ───── */

  private kick(): void {
    if (this.running && !this.raf) this.schedule();
  }

  private schedule(): void {
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = requestAnimationFrame((t) => this.tick(t));
  }

  private shouldAnimate(): boolean {
    return this.enabled && !this.reduceMotion && this.visible && this.pageVisible;
  }

  private tick(ts: number): void {
    this.raf = 0;
    if (!this.running) return;

    if (!this.visible || !this.pageVisible) return; // se reanuda via kick()

    let dt = (ts - this.lastTs) / 1000;
    this.lastTs = ts;
    if (!(dt > 0)) dt = 1 / 60;
    dt = Math.min(dt, 0.05);

    const animate = this.shouldAnimate();
    // estatico: dibuja 1 frame sin avanzar el tiempo y duerme
    this.update(animate ? dt : 0.016);
    this.draw();

    if (animate) {
      this.adapt(dt * 1000);
      this.schedule();
    }
  }

  private adapt(ms: number): void {
    this.frameMs = lerp(this.frameMs, ms, 0.05);
    if (this.frameMs > 22) {
      if (++this.slowFrames > 45) { this.quality = Math.max(0.35, this.quality - 0.15); this.slowFrames = 0; }
    } else {
      this.slowFrames = 0;
      if (this.frameMs < 11 && this.quality < 1) this.quality = Math.min(1, this.quality + 0.002);
    }
  }

  private effectiveState(): OrbState {
    if (this.transient && this.time < this.transientUntil) return this.transient;
    this.transient = null;
    // speaking vuelve a idle si dejan de llegar tokens
    if (this.sticky === "speaking" && this.time - this.lastTextAt > 0.9) this.sticky = "idle";
    return this.sticky;
  }

  private update(dt: number): void {
    this.time += dt;
    const state = this.effectiveState();
    const target = MOODS[state];
    const k = 1 - Math.exp(-dt * 4.5);
    const m = this.mood;

    (["spin", "turb", "breathe", "ringSpeed", "core", "contract", "arcRate", "speak", "trail", "energy"] as const)
      .forEach((key) => { m[key] = lerp(m[key], target[key], k); });
    const ta = state === "tool" ? this.toolTint : target.a;
    const tc = state === "tool" ? lerpRGB(this.toolTint, [255, 255, 255], 0.65) : target.c;
    m.a = lerpRGB(m.a, ta, k); m.b = lerpRGB(m.b, target.b, k); m.c = lerpRGB(m.c, tc, k);

    // envelope de voz/texto
    this.env *= Math.exp(-dt * 4.2);
    this.flash *= Math.exp(-dt * 3.2);
    this.shake *= Math.exp(-dt * 4);
    const level = Math.max(this.env, this.ext);
    for (let i = 0; i < BANDS; i++) {
      const tgt = Math.random() * level;
      this.bands[i] += (tgt - this.bands[i]) * Math.min(1, dt * 16);
    }

    // rotacion + parallax
    this.yaw += m.spin * dt * (1 + level * 0.8);
    if (this.mouseIn && !this.mini) {
      this.yawT = (this.mx - 0.5) * 0.9;
      this.pitchT = (this.my - 0.5) * 0.7;
    } else {
      this.yawT = 0; this.pitchT = Math.sin(this.time * 0.25) * 0.12;
    }
    const pk = 1 - Math.exp(-dt * 3);
    this.pitch += (this.pitchT - this.pitch) * pk;
    this.ringPhase = this.ringPhase.map((p, i) => p + dt * m.ringSpeed * (0.6 + i * 0.35) * (i === 1 ? -1 : 1));

    // rayos
    if (!this.mini || m.arcRate > 1) {
      if (Math.random() < dt * m.arcRate) this.spawnArc();
    }
    // limpieza
    this.waves = this.waves.filter((w) => -1.2 + (this.time - w.t0) * w.speed < 1.5);
    this.ripples = this.ripples.filter((r) => this.time - r.t0 < r.life);
    this.arcs = this.arcs.filter((a) => this.time - a.t0 < a.life);

    // chispas
    for (let i = 0; i < MAX_SPARKS; i++) {
      if (this.slife[i] <= 0) continue;
      this.slife[i] -= dt;
      this.sx[i] += this.svx[i] * dt; this.sy[i] += this.svy[i] * dt;
      this.svx[i] *= 0.97; this.svy[i] *= 0.97;
    }
  }

  private emitSparks(n: number, col: RGB): void {
    if (this.mini) n = Math.ceil(n / 3);
    for (let i = 0; i < n; i++) {
      const j = this.sparkHead++ % MAX_SPARKS;
      const a = Math.random() * TAU;
      const sp = (0.6 + Math.random() * 1.4) * (this.R || 50);
      this.sx[j] = Math.cos(a) * this.R * 0.9; this.sy[j] = Math.sin(a) * this.R * 0.9;
      this.svx[j] = Math.cos(a) * sp; this.svy[j] = Math.sin(a) * sp;
      this.slife[j] = 0.5 + Math.random() * 0.6;
      this.scol[j] = col;
    }
  }

  private spawnArc(): void {
    const rv = (): [number, number, number] => {
      const y = Math.random() * 2 - 1, a = Math.random() * TAU, r = Math.sqrt(1 - y * y);
      return [Math.cos(a) * r, y, Math.sin(a) * r];
    };
    const A = rv(); let B = rv();
    // evita puntos casi iguales
    if (A[0] * B[0] + A[1] * B[1] + A[2] * B[2] > 0.9) B = [-A[0], A[1], -A[2]];
    const n = 14, pts: number[] = [];
    const lift = 0.12 + Math.random() * 0.18;
    for (let i = 0; i <= n; i++) {
      const t = i / n;
      let x = lerp(A[0], B[0], t), y = lerp(A[1], B[1], t), z = lerp(A[2], B[2], t);
      const l = Math.hypot(x, y, z) || 1;
      const rr = 1.02 + lift * Math.sin(Math.PI * t) + (i > 0 && i < n ? (Math.random() - 0.5) * 0.06 : 0);
      x = (x / l) * rr; y = (y / l) * rr; z = (z / l) * rr;
      pts.push(x, y, z);
    }
    this.arcs.push({ pts, t0: this.time, life: 0.32 + Math.random() * 0.2, col: Math.random() < 0.5 ? this.mood.c : this.mood.a });
    if (this.arcs.length > 10) this.arcs.shift();
  }

  /* ───── dibujo ───── */

  private draw(): void {
    const { ctx, w, h, R, dpr, mood: m } = this;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    // estela: desvanece lo anterior dejando fondo transparente
    ctx.globalCompositeOperation = "destination-out";
    ctx.fillStyle = `rgba(0,0,0,${clamp(0.62 - 0.5 * m.trail, 0.08, 0.7).toFixed(3)})`;
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "lighter";

    const sh = this.shake * R * 0.05;
    const cx = w / 2 + (Math.random() - 0.5) * sh + (this.mouseIn ? (this.mx - 0.5) * R * 0.06 : 0);
    const cy = h / 2 + (Math.random() - 0.5) * sh;

    const level = Math.max(this.env, this.ext);
    const breath = Math.sin(this.time * m.breathe * TAU) * 0.025 + level * 0.04;
    const rScale = m.contract * (1 + breath) + this.flash * 0.05;

    // halo + nucleo
    const haloA = 0.06 + 0.1 * m.energy + this.flash * 0.1;
    let g = ctx.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.9);
    g.addColorStop(0, rgba(m.a, haloA)); g.addColorStop(1, rgba(m.a, 0));
    ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);

    const coreR = R * (0.55 + 0.2 * level + this.flash * 0.25) * rScale;
    const coreA = clamp(0.18 + 0.45 * m.core + this.flash * 0.35, 0, 1);
    g = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
    g.addColorStop(0, rgba(lerpRGB(m.c, [255, 255, 255], 0.5), coreA));
    g.addColorStop(0.4, rgba(m.c, coreA * 0.45));
    g.addColorStop(1, rgba(m.c, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, coreR, 0, TAU); ctx.fill();

    // rotacion global precalculada
    const cyw = Math.cos(this.yaw), syw = Math.sin(this.yaw);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    const proj = (x: number, y: number, z: number): [number, number, number, number] => {
      const x1 = x * cyw + z * syw, z1 = -x * syw + z * cyw;
      const y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      const s = 1 / (1 - z2 * 0.28);
      return [cx + x1 * R * s, cy + y2 * R * s, z2, s];
    };

    this.drawRings(proj, false);
    this.drawParticles(cx, cy, cyw, syw, cp, sp, rScale, level);
    this.drawRings(proj, true);
    this.drawArcs(proj);
    this.drawRipples(cx, cy);
    this.drawSparks(cx, cy);

    ctx.globalCompositeOperation = "source-over";
  }

  private drawParticles(
    cx: number, cy: number, cyw: number, syw: number, cp: number, sp: number,
    rScale: number, level: number,
  ): void {
    const { ctx, R, mood: m, time: t } = this;
    const n = Math.floor(this.N * this.quality);
    const sizeK = clamp(R / 110, 0.45, 1.6);
    this.counts.fill(0);
    const turb = m.turb + level * 0.05;
    const speak = m.speak * 0.22;

    for (let i = 0; i < n; i++) {
      const x = this.nx[i], y = this.ny[i], z = this.nz[i];
      let d = turb * noise(x * 1.6, y * 1.6, z * 1.6, t * 0.6 + this.pphase[i] * 0.02);

      if (speak > 0.001) {
        const band = Math.floor(((Math.atan2(z, x) + Math.PI) / TAU) * BANDS) % BANDS;
        d += this.bands[band] * speak * (1 - Math.abs(y) * 0.35);
      }
      for (let wi = 0; wi < this.waves.length; wi++) {
        const wv = this.waves[wi];
        const front = -1.2 + (t - wv.t0) * wv.speed;
        const q = (y - front) / wv.width;
        d += wv.amp * Math.exp(-q * q);
      }
      // las capas interiores se deforman menos
      const r = this.pr0[i] * (1 + d * (this.pr0[i] > 0.85 ? 1 : 0.4)) * rScale;

      const x1 = x * cyw + z * syw, z1 = -x * syw + z * cyw;
      const y2 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;
      const s = 1 / (1 - z2 * r * 0.28);
      this.px[i] = cx + x1 * r * R * s;
      this.py[i] = cy + y2 * r * R * s;
      this.prad[i] = this.psize[i] * sizeK * s * (0.85 + 0.3 * Math.sin(t * 2 + this.pphase[i]));

      const di = Math.min(BUCKET_DEPTH - 1, Math.floor(((z2 + 1) / 2) * BUCKET_DEPTH));
      const b = this.pmix[i] * BUCKET_DEPTH + di;
      this.lists[b][this.counts[b]++] = i;
    }

    const bright = 0.5 + 0.5 * m.energy;
    for (let mi = 0; mi < BUCKET_MIX; mi++) {
      const col = lerpRGB(m.a, m.b, mi / (BUCKET_MIX - 1));
      for (let di = 0; di < BUCKET_DEPTH; di++) {
        const b = mi * BUCKET_DEPTH + di;
        const c = this.counts[b];
        if (!c) continue;
        ctx.fillStyle = rgba(col, (0.12 + 0.75 * ((di + 0.5) / BUCKET_DEPTH)) * bright);
        ctx.beginPath();
        const list = this.lists[b];
        for (let k = 0; k < c; k++) {
          const i = list[k], rd = this.prad[i], x = this.px[i], y = this.py[i];
          ctx.moveTo(x + rd, y);
          ctx.arc(x, y, rd, 0, TAU);
        }
        ctx.fill();
      }
    }
  }

  private drawRings(proj: (x: number, y: number, z: number) => [number, number, number, number], front: boolean): void {
    if (this.mini && !front) return;
    const { ctx, mood: m } = this;
    const radii = [1.22, 1.4, 1.62];
    const tiltX = [0.35, -0.9, 1.25];
    const tiltZ = [0.2, 0.7, -0.5];
    const vis = (0.12 + 0.3 * m.energy) * (front ? 1 : 0.55);
    const segs = this.mini ? 36 : 72;
    const count = this.mini ? 1 : 3;

    for (let r = 0; r < count; r++) {
      const ctr = Math.cos(tiltX[r]), str = Math.sin(tiltX[r]);
      const ctz = Math.cos(tiltZ[r]), stz = Math.sin(tiltZ[r]);
      const col = lerpRGB(m.a, m.b, r / 2);
      const pt = (th: number) => {
        let x = Math.cos(th) * radii[r], y = 0, z = Math.sin(th) * radii[r];
        const y1 = y * ctr - z * str, z1 = y * str + z * ctr; y = y1; z = z1;
        const x2 = x * ctz - y * stz, y2 = x * stz + y * ctz;
        return proj(x2, y2, z);
      };
      ctx.strokeStyle = rgba(col, vis);
      ctx.lineWidth = front ? 1.2 : 0.8;
      ctx.beginPath();
      let prev = pt(0);
      for (let i = 1; i <= segs; i++) {
        const cur = pt((i / segs) * TAU);
        const isFront = (prev[2] + cur[2]) * 0.5 > 0;
        if (isFront === front) { ctx.moveTo(prev[0], prev[1]); ctx.lineTo(cur[0], cur[1]); }
        prev = cur;
      }
      ctx.stroke();

      // satelite
      const th = this.ringPhase[r];
      const s = pt(th);
      if ((s[2] > 0) === front) {
        const sz = (this.mini ? 1.6 : 2.6) * s[3];
        ctx.fillStyle = rgba(m.c, 0.25 + 0.4 * m.energy);
        ctx.beginPath(); ctx.arc(s[0], s[1], sz * 2.4, 0, TAU); ctx.fill();
        ctx.fillStyle = rgba([255, 255, 255], 0.85);
        ctx.beginPath(); ctx.arc(s[0], s[1], sz, 0, TAU); ctx.fill();
      }
    }
  }

  private drawArcs(proj: (x: number, y: number, z: number) => [number, number, number, number]): void {
    const { ctx, time: t } = this;
    for (const a of this.arcs) {
      const age = (t - a.t0) / a.life;
      const alpha = Math.sin(clamp(age, 0, 1) * Math.PI);
      for (let pass = 0; pass < 2; pass++) {
        ctx.strokeStyle = rgba(pass ? ([255, 255, 255] as RGB) : a.col, alpha * (pass ? 0.9 : 0.35));
        ctx.lineWidth = pass ? 1 : 3;
        ctx.beginPath();
        for (let i = 0; i < a.pts.length; i += 3) {
          const p = proj(a.pts[i], a.pts[i + 1], a.pts[i + 2]);
          if (i === 0) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
        }
        ctx.stroke();
      }
    }
  }

  private drawRipples(cx: number, cy: number): void {
    const { ctx, R, time: t } = this;
    for (const r of this.ripples) {
      const age = (t - r.t0) / r.life;
      ctx.strokeStyle = rgba(r.col, (1 - age) * r.amp);
      ctx.lineWidth = 1.5 * (1 - age) + 0.5;
      ctx.beginPath();
      ctx.arc(cx, cy, R * (1.05 + age * 0.9), 0, TAU);
      ctx.stroke();
    }
  }

  private drawSparks(cx: number, cy: number): void {
    const { ctx } = this;
    for (let i = 0; i < MAX_SPARKS; i++) {
      const l = this.slife[i];
      if (l <= 0) continue;
      ctx.fillStyle = rgba(this.scol[i], clamp(l * 1.6, 0, 1));
      ctx.beginPath();
      ctx.arc(cx + this.sx[i], cy + this.sy[i], this.mini ? 0.8 : 1.4, 0, TAU);
      ctx.fill();
    }
  }
}
