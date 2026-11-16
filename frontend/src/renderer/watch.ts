// renderer/watch.ts — Nex Watch: campana de alertas + panel
import { API_BASE } from "./api";

interface WatchAlert {
  kind: string;
  message: string;
  details: Record<string, unknown>;
  timestamp: string;
}

const KIND_ICONS: Record<string, string> = {
  mass_delete: "🚨",
  secret_found: "🔑",
  sensitive_file: "📄",
  sensitive_delete: "🗑️",
  dangerous_command: "⚠️",
};

let open = false;
let pollTimer: number | null = null;

function renderAlerts(alerts: WatchAlert[]): void {
  const list = document.getElementById("alerts-list");
  if (!list) return;

  if (!alerts.length) {
    list.innerHTML = `<p class="panel-desc">✅ Sin alertas recientes.</p>`;
  } else {
    list.innerHTML = alerts
      .map((a) => {
        const icon = KIND_ICONS[a.kind] || "🔔";
        const extra = a.details.file ? `<span class="text-white/30 text-[11px]"> — ${a.details.file}</span>` : "";
        return `<div class="alert-item"><span class="alert-kind">${icon} ${a.kind}</span><span class="text-white/70">${a.message}</span><span class="text-white/30 text-[11px]">${a.timestamp}</span>${extra}</div>`;
      })
      .join("");
  }
}

async function refreshAlerts(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/alerts?limit=50`);
    if (!res.ok) return;
    const data = await res.json();
    const alerts: WatchAlert[] = data.alerts || [];

    renderAlerts(alerts);

    const badge = document.getElementById("watch-badge");
    const count = alerts.length;
    if (badge) {
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.style.display = count > 0 ? "flex" : "none";
    }
  } catch {
    /* backend apagado */
  }
}

function buildPanel(): void {
  const root = document.getElementById("watch-root");
  if (!root) return;

  root.innerHTML = `
    <div style="position:relative">
      <button id="watch-trigger" class="settings-btn" aria-label="Nex Watch alerts" title="Alertas de Nex Watch">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
        <span id="watch-badge" style="display:none; position:absolute; top:-6px; right:-6px; background:#ef4444; color:white; font-size:10px; min-width:16px; height:16px; border-radius:8px; align-items:center; justify-content:center; padding:0 4px; font-weight:700"></span>
      </button>
      <div id="watch-panel" style="display:none; position:absolute; top:44px; right:0; width:340px; background:#1a1a24; border:1px solid rgba(255,255,255,0.08); border-radius:12px; padding:12px; box-shadow:0 10px 30px rgba(0,0,0,0.5); z-index:60">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
          <span style="font-weight:700; font-size:13px; color:rgba(255,255,255,0.9)">🛡️ Nex Watch</span>
          <button id="watch-panel-close" style="background:none; border:none; color:rgba(255,255,255,0.5); cursor:pointer; font-size:14px">✕</button>
        </div>
        <div id="watch-alerts-list" style="max-height:300px; overflow-y:auto; display:flex; flex-direction:column; gap:8px; font-size:12px"></div>
        <div style="display:flex; gap:8px; margin-top:10px">
          <button id="watch-refresh-btn" style="flex:1; background:rgba(255,255,255,0.06); border:none; color:rgba(255,255,255,0.8); padding:6px; border-radius:8px; cursor:pointer; font-size:12px">🔄 Refrescar</button>
          <button id="watch-clear-btn" style="flex:1; background:rgba(239,68,68,0.15); border:none; color:#f87171; padding:6px; border-radius:8px; cursor:pointer; font-size:12px">🗑 Limpiar</button>
        </div>
      </div>
    </div>
  `;

  const trigger = document.getElementById("watch-trigger");
  const panel = document.getElementById("watch-panel");
  const closeBtn = document.getElementById("watch-panel-close");

  trigger?.addEventListener("click", () => {
    open = !open;
    if (panel) panel.style.display = open ? "block" : "none";
    if (open) {
      void refreshAlerts();
      const list = document.getElementById("watch-alerts-list");
      if (list) {
        const inner = document.getElementById("alerts-list");
        if (inner) list.innerHTML = inner.innerHTML;
      }
    }
  });
  closeBtn?.addEventListener("click", () => {
    open = false;
    if (panel) panel.style.display = "none";
  });
  document.getElementById("watch-refresh-btn")?.addEventListener("click", () => {
    void refreshAlerts();
    const list = document.getElementById("watch-alerts-list");
    const inner = document.getElementById("alerts-list");
    if (list && inner) list.innerHTML = inner.innerHTML;
  });
  document.getElementById("watch-clear-btn")?.addEventListener("click", async () => {
    try {
      await fetch(`${API_BASE}/api/v1/alerts/clear`, { method: "POST" });
      void refreshAlerts();
      const list = document.getElementById("watch-alerts-list");
      const inner = document.getElementById("alerts-list");
      if (list && inner) list.innerHTML = inner.innerHTML;
    } catch {
      /* ignore */
    }
  });
}

export function refreshAlertsFromSettings(): void {
  void refreshAlerts();
}

export function initWatch(): void {
  buildPanel();
  void refreshAlerts();
  pollTimer = window.setInterval(() => void refreshAlerts(), 10000);
}
