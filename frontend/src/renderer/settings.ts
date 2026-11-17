import type { ProviderInfo } from "../types";
import type { Locale } from "../i18n/locales";
import { t, setLocale, applyTranslationsToDOM } from "../i18n/index";
import { API_BASE, apiGet, apiPost } from "./api";
import { $, setSelect, setInput, setCheck } from "./ui";

let currentProviders: ProviderInfo[] = [];

export function initSettings(): void {
  const settingsTrigger = $<HTMLButtonElement>("settings-trigger");
  const settingsOverlay = $<HTMLElement>("settings-overlay");
  const settingsCloseBtn = $<HTMLButtonElement>("settings-close-btn");
  const radiusSlider = $<HTMLInputElement>("setting-radius");
  const radiusValue = $<HTMLElement>("radius-value");

  settingsTrigger.addEventListener("click", () => {
    settingsOverlay.classList.add("open");
    loadAllSettings();
  });
  settingsCloseBtn.addEventListener("click", () => {
    settingsOverlay.classList.remove("open");
  });
  settingsOverlay.addEventListener("click", (e) => {
    if (e.target === settingsOverlay) settingsOverlay.classList.remove("open");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && settingsOverlay.classList.contains("open")) {
      settingsOverlay.classList.remove("open");
    }
  });

  document.querySelectorAll(".settings-nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".settings-nav-item").forEach((n) => n.classList.remove("active"));
      document.querySelectorAll(".settings-panel").forEach((p) => p.classList.remove("active"));
      item.classList.add("active");
      const panel = document.getElementById("panel-" + (item as HTMLElement).dataset.section);
      if (panel) panel.classList.add("active");
    });
  });

  radiusSlider.addEventListener("input", () => {
    const v = parseInt(radiusSlider.value);
    document.documentElement.style.setProperty("--interface-radius", v + "px");
    radiusValue.textContent = v + "px";
    localStorage.setItem("nex_interface_radius", String(v));
    saveSetting("interface_radius", v);
  });

  const fontSizeSlider = document.getElementById("setting-font-size") as HTMLInputElement;
  const fontSizeVal = document.getElementById("font-size-value") as HTMLElement;
  fontSizeSlider?.addEventListener("input", () => {
    const v = parseInt(fontSizeSlider.value);
    fontSizeVal.textContent = v + "px";
    document.documentElement.style.setProperty("--base-font-size", v + "px");
    saveSetting("font_size", v);
  });

  document.getElementById("setting-theme")?.addEventListener("change", (e) => {
    saveSetting("theme", (e.target as HTMLSelectElement).value);
  });
  document.getElementById("setting-language")?.addEventListener("change", (e) => {
    const lang = (e.target as HTMLSelectElement).value as Locale;
    setLocale(lang);
    applyTranslationsToDOM();
    saveSetting("language", lang);
  });
  document.getElementById("setting-animations")?.addEventListener("change", (e) => {
    const on = (e.target as HTMLInputElement).checked;
    saveSetting("animations_enabled", on);
    document.documentElement.style.setProperty("--animations", on ? "1" : "0");
  });
  document.getElementById("setting-compact-mode")?.addEventListener("change", (e) => {
    saveSetting("compact_mode", (e.target as HTMLInputElement).checked);
  });
  document.getElementById("setting-orb-animation")?.addEventListener("change", (e) => {
    const on = (e.target as HTMLInputElement).checked;
    saveSetting("orb_animation", on);
    (window as any).__nexOrb?.setEnabled(on);
    (window as any).__miniOrb?.setEnabled(on);
  });
  document.getElementById("setting-accent-color")?.addEventListener("input", (e) => {
    applyAccentColor((e.target as HTMLInputElement).value);
    saveSetting("accent_color", (e.target as HTMLInputElement).value);
  });
  document.getElementById("setting-font-family")?.addEventListener("change", (e) => {
    const font = (e.target as HTMLSelectElement).value;
    document.documentElement.style.setProperty("--font-family", font);
    document.body.style.fontFamily = font;
    saveSetting("font_family", font);
  });
  document.getElementById("setting-sidebar-visible")?.addEventListener("change", (e) => {
    const visible = (e.target as HTMLInputElement).checked;
    const sidebar = document.getElementById("sidebar");
    const handle = document.getElementById("sidebar-drag-handle");
    if (sidebar) sidebar.style.display = visible ? "" : "none";
    if (handle) handle.style.display = visible ? "" : "none";
    saveSetting("sidebar_visible", visible);
  });
  document.getElementById("setting-auto-title")?.addEventListener("change", (e) => {
    saveSetting("auto_title", (e.target as HTMLInputElement).checked);
  });
  document.getElementById("setting-confirm-delete")?.addEventListener("change", (e) => {
    saveSetting("confirm_delete", (e.target as HTMLInputElement).checked);
  });

  // ── Security (explainer + scan scope) ──
  document.getElementById("setting-explain-mode")?.addEventListener("change", (e) => {
    saveSetting("explain_mode", (e.target as HTMLInputElement).checked);
  });
  document.getElementById("setting-scan-allowlist")?.addEventListener("change", (e) => {
    saveSetting("scan_allowlist", (e.target as HTMLInputElement).value.trim());
  });
  document.getElementById("quick-reset-btn")?.addEventListener("click", async () => {
    if (!confirm("Reset appearance to defaults?")) return;
    applyAccentColor("#6366f1");
    const colorInput = document.getElementById("setting-accent-color") as HTMLInputElement;
    if (colorInput) colorInput.value = "#6366f1";
    saveSetting("accent_color", "#6366f1");
    document.documentElement.style.setProperty("--font-family", "'Inter', system-ui, -apple-system, sans-serif");
    document.body.style.fontFamily = "'Inter', system-ui, -apple-system, sans-serif";
    setSelect("setting-font-family", "'Inter', system-ui, -apple-system, sans-serif");
    saveSetting("font_family", "'Inter', system-ui, -apple-system, sans-serif");
    document.documentElement.style.setProperty("--sidebar-width", "270px");
    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.style.display = "";
    const handle = document.getElementById("sidebar-drag-handle");
    if (handle) handle.style.display = "";
    const visCheck = document.getElementById("setting-sidebar-visible") as HTMLInputElement;
    if (visCheck) { visCheck.checked = true; }
    saveSetting("sidebar_visible", true);
    saveSetting("sidebar_width", 270);
    document.documentElement.style.setProperty("--interface-radius", "12px");
    radiusSlider.value = "12";
    radiusValue.textContent = "12px";
    localStorage.setItem("nex_interface_radius", "12");
    saveSetting("interface_radius", 12);
  });

  initSidebarDrag();

  document.getElementById("setting-context-size")?.addEventListener("input", (e) => {
    saveSetting("context_size", parseInt((e.target as HTMLInputElement).value));
  });
  document.getElementById("setting-max-sessions")?.addEventListener("change", (e) => {
    saveSetting("max_sessions", parseInt((e.target as HTMLInputElement).value));
  });

  const tempSlider = document.getElementById("setting-temperature") as HTMLInputElement;
  const tempVal = document.getElementById("temperature-value") as HTMLElement;
  tempSlider?.addEventListener("input", () => {
    const v = parseFloat(tempSlider.value);
    tempVal.textContent = v.toFixed(2);
    saveSetting("temperature", v);
  });
  const topPSlider = document.getElementById("setting-top-p") as HTMLInputElement;
  const topPVal = document.getElementById("top-p-value") as HTMLElement;
  topPSlider?.addEventListener("input", () => {
    const v = parseFloat(topPSlider.value);
    topPVal.textContent = v.toFixed(2);
    saveSetting("top_p", v);
  });
  document.getElementById("setting-max-tokens")?.addEventListener("change", (e) => {
    saveSetting("max_tokens", parseInt((e.target as HTMLInputElement).value));
  });
  document.getElementById("setting-send-mode")?.addEventListener("change", (e) => {
    saveSetting("send_mode", (e.target as HTMLSelectElement).value);
  });
  document.getElementById("setting-auto-scroll")?.addEventListener("change", (e) => {
    saveSetting("auto_scroll", (e.target as HTMLInputElement).checked);
  });
  document.getElementById("setting-timestamps")?.addEventListener("change", (e) => {
    saveSetting("show_timestamps", (e.target as HTMLInputElement).checked);
  });
  document.getElementById("setting-syntax-highlighting")?.addEventListener("change", (e) => {
    saveSetting("syntax_highlighting", (e.target as HTMLInputElement).checked);
  });

  const provSelect = document.getElementById("setting-provider") as HTMLSelectElement;
  provSelect?.addEventListener("change", () => {
    saveSetting("provider", provSelect.value);
    loadModelsForProvider(provSelect.value);
  });
  const modelSelect = document.getElementById("setting-model") as HTMLSelectElement;
  modelSelect?.addEventListener("change", () => {
    saveSetting("model", modelSelect.value);
  });
  document.getElementById("refresh-models-btn")?.addEventListener("click", () => {
    const prov = (document.getElementById("setting-provider") as HTMLSelectElement).value;
    loadModelsForProvider(prov);
  });

  document.getElementById("setting-url-openai")?.addEventListener("change", (e) => {
    saveSetting("custom_api_urls", { openai: (e.target as HTMLInputElement).value });
  });
  document.getElementById("setting-url-ollama")?.addEventListener("change", (e) => {
    saveSetting("custom_api_urls", { ollama: (e.target as HTMLInputElement).value });
  });
  document.getElementById("setting-timeout")?.addEventListener("change", (e) => {
    saveSetting("timeout", parseInt((e.target as HTMLInputElement).value));
  });
  document.getElementById("save-keys-btn")?.addEventListener("click", saveApiKeys);
  document.getElementById("setting-system-prompt")?.addEventListener("change", (e) => {
    saveSetting("system_prompt", (e.target as HTMLTextAreaElement).value);
  });
  document.getElementById("setting-max-tool-calls")?.addEventListener("change", (e) => {
    saveSetting("max_tool_calls", parseInt((e.target as HTMLInputElement).value));
  });
  document.getElementById("setting-auto-save")?.addEventListener("change", (e) => {
    saveSetting("auto_save_interval", parseInt((e.target as HTMLInputElement).value));
  });

  document.getElementById("export-settings-btn")?.addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/settings/export`);
      const data = await res.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "nex-settings.json"; a.click();
      URL.revokeObjectURL(url);
    } catch {}
  });
  document.getElementById("import-settings-btn")?.addEventListener("click", () => {
    document.getElementById("import-file-input")?.click();
  });
  document.getElementById("import-file-input")?.addEventListener("change", async (e) => {
    const input = e.target as HTMLInputElement;
    if (!input.files?.length) return;
    try {
      const text = await input.files[0].text();
      const data = JSON.parse(text);
      await fetch(`${API_BASE}/api/v1/settings/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      loadAllSettings();
    } catch {}
    input.value = "";
  });
  document.getElementById("clear-history-btn")?.addEventListener("click", async () => {
    if (!confirm(t("settings.dataTab.clearHistoryConfirm", "Clear all chat history? This action cannot be undone."))) return;
    try {
      await fetch(`${API_BASE}/api/v1/clear-history`, { method: "POST" });
    } catch {}
  });
  document.getElementById("reset-settings-btn")?.addEventListener("click", async () => {
    if (!confirm(t("settings.dataTab.resetSettingsConfirm", "Reset all settings to defaults?"))) return;
    try {
      await fetch(`${API_BASE}/api/v1/settings/reset`, { method: "POST" });
      localStorage.removeItem("nex_interface_radius");
      document.documentElement.style.setProperty("--interface-radius", "12px");
      radiusSlider.value = "12";
      radiusValue.textContent = "12px";
      const fontSizeSlider2 = document.getElementById("setting-font-size") as HTMLInputElement;
      if (fontSizeSlider2) {
        fontSizeSlider2.value = "14";
        document.getElementById("font-size-value")!.textContent = "14px";
      }
      loadAllSettings();
    } catch {}
  });
}

async function loadAllSettings(): Promise<void> {
  const data = await apiGet<any>("/api/v1/settings");
  if (data) applySettingsToUI(data);
}

function applySettingsToUI(data: any): void {
  setSelect("setting-theme", data.theme);
  setSelect("setting-language", data.language);

  if (data.font_size) {
    const fs = document.getElementById("setting-font-size") as HTMLInputElement;
    const fsv = document.getElementById("font-size-value") as HTMLElement;
    if (fs) { fs.value = String(data.font_size); fsv.textContent = data.font_size + "px"; }
    document.documentElement.style.setProperty("--base-font-size", data.font_size + "px");
  }

  const radiusSlider = $<HTMLInputElement>("setting-radius");
  const radiusValue = $<HTMLElement>("radius-value");
  if (data.interface_radius != null) {
    radiusSlider.value = String(data.interface_radius);
    radiusValue.textContent = data.interface_radius + "px";
    document.documentElement.style.setProperty("--interface-radius", data.interface_radius + "px");
    localStorage.setItem("nex_interface_radius", String(data.interface_radius));
  }

  const animCheck = document.getElementById("setting-animations") as HTMLInputElement;
  if (animCheck) animCheck.checked = data.animations_enabled !== false;

  if (data.temperature != null) {
    const ts = document.getElementById("setting-temperature") as HTMLInputElement;
    const tv = document.getElementById("temperature-value") as HTMLElement;
    if (ts) { ts.value = String(data.temperature); tv.textContent = parseFloat(String(data.temperature)).toFixed(2); }
  }
  if (data.top_p != null) {
    const tp = document.getElementById("setting-top-p") as HTMLInputElement;
    const tpv = document.getElementById("top-p-value") as HTMLElement;
    if (tp) { tp.value = String(data.top_p); tpv.textContent = parseFloat(String(data.top_p)).toFixed(2); }
  }
  setInput("setting-max-tokens", data.max_tokens);
  setSelect("setting-send-mode", data.send_mode);
  setCheck("setting-auto-scroll", data.auto_scroll);
  setCheck("setting-timestamps", data.show_timestamps);
  setCheck("setting-syntax-highlighting", data.syntax_highlighting);

  currentProviders = data.providers || [];
  const provSelect = document.getElementById("setting-provider") as HTMLSelectElement;
  if (provSelect) {
    provSelect.innerHTML = currentProviders
      .map((p: any) => `<option value="${p.name}" ${p.name === data.provider ? "selected" : ""}>${p.name}${p.models?.length ? ` (${p.models.length} modelos)` : ""}</option>`)
      .join("");
    const activeProv = currentProviders.find((p: any) => p.name === data.provider);
    const models = activeProv?.models || [];
    const modelSelect = document.getElementById("setting-model") as HTMLSelectElement;
    if (modelSelect) {
      if (models.length > 0) {
        modelSelect.innerHTML = models.map((m: string) => `<option value="${m}" ${m === data.model ? "selected" : ""}>${m}</option>`).join("");
      } else {
        modelSelect.innerHTML = `<option value="${data.model}" selected>${data.model}</option>`;
      }
    }
  }

  loadOllamaModels();

  const urls = data.custom_api_urls || {};
  setInput("setting-url-openai", urls.openai || "");
  setInput("setting-url-ollama", urls.ollama || "");
  setInput("setting-timeout", data.timeout ?? 60);

  setInput("setting-max-sessions", data.max_sessions);
  setCheck("setting-compact-mode", data.compact_mode);
  setCheck("setting-orb-animation", data.orb_animation);
  const orbOn = data.orb_animation !== false;
  (window as any).__nexOrb?.setEnabled(orbOn);
  (window as any).__miniOrb?.setEnabled(orbOn);

  if (data.accent_color) {
    applyAccentColor(data.accent_color);
    const colorInput = document.getElementById("setting-accent-color") as HTMLInputElement;
    if (colorInput) colorInput.value = data.accent_color;
  }
  if (data.font_family) {
    document.documentElement.style.setProperty("--font-family", data.font_family);
    document.body.style.fontFamily = data.font_family;
    setSelect("setting-font-family", data.font_family);
  }
  setCheck("setting-sidebar-visible", data.sidebar_visible !== false);
  const sidebarVis = document.getElementById("sidebar");
  const handleVis = document.getElementById("sidebar-drag-handle");
  if (sidebarVis) sidebarVis.style.display = data.sidebar_visible !== false ? "" : "none";
  if (handleVis) handleVis.style.display = data.sidebar_visible !== false ? "" : "none";
  setCheck("setting-auto-title", data.auto_title !== false);
  setCheck("setting-confirm-delete", data.confirm_delete !== false);
  if (data.sidebar_width) {
    document.documentElement.style.setProperty("--sidebar-width", data.sidebar_width + "px");
  }

  const ctxSlider = document.getElementById("setting-context-size") as HTMLInputElement;
  const ctxVal = document.getElementById("context-size-value") as HTMLElement;
  if (ctxSlider && data.context_size != null) {
    ctxSlider.value = String(data.context_size);
    if (ctxVal) ctxVal.textContent = data.context_size + "k";
  }

  const sp = document.getElementById("setting-system-prompt") as HTMLTextAreaElement;
  if (sp && data.system_prompt) sp.value = data.system_prompt;
  setInput("setting-max-tool-calls", data.max_tool_calls);
  setInput("setting-auto-save", data.auto_save_interval);

  setCheck("setting-explain-mode", data.explain_mode !== false);
  const allowlistInput = document.getElementById("setting-scan-allowlist") as HTMLInputElement;
  if (allowlistInput) allowlistInput.value = data.scan_allowlist || "127.0.0.1";
}

function initSidebarDrag(): void {
  const handle = document.getElementById("sidebar-drag-handle");
  const sidebar = document.getElementById("sidebar");
  if (!handle || !sidebar) return;

  let isDragging = false;
  handle.addEventListener("mousedown", (e) => {
    isDragging = true;
    handle.classList.add("active");
    e.preventDefault();
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });
  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const width = Math.max(180, Math.min(500, e.clientX));
    document.documentElement.style.setProperty("--sidebar-width", width + "px");
  });
  document.addEventListener("mouseup", () => {
    if (!isDragging) return;
    isDragging = false;
    handle.classList.remove("active");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    const w = parseInt(getComputedStyle(sidebar).width);
    saveSetting("sidebar_width", w);
  });
}

async function loadOllamaModels(): Promise<void> {
  const data = await apiGet<{ models: string[] }>("/api/v1/ollama/models");
  if (!data) return;
  const provSelect = document.getElementById("setting-provider") as HTMLSelectElement;
  if (!provSelect) return;

  if (data.models?.length > 0) {
    const existing = Array.from(provSelect.options).find((o) => o.value === "ollama");
    if (!existing) {
      const opt = document.createElement("option");
      opt.value = "ollama";
      opt.textContent = `ollama (${data.models.length} modelos locales)`;
      provSelect.appendChild(opt);
    }
  }
  if (provSelect.value === "ollama" && data.models?.length) {
    const modelSelect = document.getElementById("setting-model") as HTMLSelectElement;
    if (modelSelect) {
      modelSelect.innerHTML = data.models.map((m: string) => `<option value="${m}">${m}</option>`).join("");
    }
  }
}

async function loadModelsForProvider(providerName: string): Promise<void> {
  const modelSelect = document.getElementById("setting-model") as HTMLSelectElement;
  if (!modelSelect) return;

  if (providerName === "ollama") {
    const data = await apiGet<{ models: string[] }>("/api/v1/ollama/models");
    if (data?.models?.length) {
      modelSelect.innerHTML = data.models.map((m: string) => `<option value="${m}">${m}</option>`).join("");
      return;
    }
    modelSelect.innerHTML = '<option value="">No hay modelos Ollama</option>';
    return;
  }

  const provider = currentProviders.find((p) => p.name === providerName);
  const models = provider?.models || [];
  modelSelect.innerHTML = models.length > 0
    ? models.map((m: string) => `<option value="${m}">${m}</option>`).join("")
    : '<option value="">Seleccionar modelo</option>';
}

async function saveSetting(key: string, value: any): Promise<void> {
  await apiPost("/api/v1/settings", { [key]: value });
}

async function saveApiKeys(): Promise<void> {
  const keys: Record<string, string> = {};
  for (const p of ["gemini", "openai", "anthropic", "deepseek"]) {
    const input = document.getElementById(`key-${p}`) as HTMLInputElement;
    if (input && input.value.trim()) keys[p] = input.value.trim();
  }
  if (Object.keys(keys).length === 0) return;

  try {
    const res = await fetch(`${API_BASE}/api/v1/settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_keys: keys }),
    });
    if (res.ok) {
      const msg = document.getElementById("keys-saved-msg");
      if (msg) { msg.style.display = "block"; setTimeout(() => { msg.style.display = "none"; }, 3000); }
      for (const p of ["gemini", "openai", "anthropic", "deepseek"]) {
        const input = document.getElementById(`key-${p}`) as HTMLInputElement;
        if (input) input.value = "";
      }
    }
  } catch {}
}

function applyAccentColor(hex: string): void {
  document.documentElement.style.setProperty("--accent", hex);
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  document.documentElement.style.setProperty("--accent-rgb", `${r}, ${g}, ${b}`);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  let safeR = r, safeG = g, safeB = b;
  if (lum < 0.25) {
    const maxChannel = Math.max(r, g, b, 1);
    const scale = Math.max(180 / maxChannel, 3);
    safeR = Math.min(255, Math.round(r * scale));
    safeG = Math.min(255, Math.round(g * scale));
    safeB = Math.min(255, Math.round(b * scale));
  }
  document.documentElement.style.setProperty("--accent-safe-rgb", `${safeR}, ${safeG}, ${safeB}`);
  const lightR = Math.min(255, safeR + 30);
  const lightG = Math.min(255, safeG + 30);
  const lightB = Math.min(255, safeB + 30);
  document.documentElement.style.setProperty("--accent-light-rgb", `${lightR}, ${lightG}, ${lightB}`);
  const v100 = (v: number) => Math.round(v + (255 - v) * 0.6);
  document.documentElement.style.setProperty("--accent-100-rgb", `${v100(safeR)}, ${v100(safeG)}, ${v100(safeB)}`);
  const v200 = (v: number) => Math.round(v + (255 - v) * 0.3);
  document.documentElement.style.setProperty("--accent-200-rgb", `${v200(safeR)}, ${v200(safeG)}, ${v200(safeB)}`);
}
