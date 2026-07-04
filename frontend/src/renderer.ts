import type { Message, ChatSession, SessionGroup, SystemMetrics } from "./types";

interface NetosAPI {
  sendMessage: (message: string) => Promise<{ success: boolean; response: string }>;
}

declare global {
  interface Window {
    netosAPI?: NetosAPI;
  }
}

import { marked } from "marked";
import { saveSessions, loadSessions } from "./renderer/history";
import { PlasmaCore } from "./renderer/plasma-core";
import { WELCOME_MESSAGES, getRandomWelcomeMessage } from "./renderer/welcomeMessages";

const API_BASE = "http://127.0.0.1:8765";

marked.use({
  renderer: {
    code(token: any) {
      const codeText = token.text || "";
      const lang = (token.lang || "").trim();
      const displayLang = lang || "code";
      const escapedCode = codeText
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
      return `
        <div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-block-lang">${displayLang}</span>
            <button class="copy-code-btn">Copiar</button>
          </div>
          <pre><code class="language-${displayLang}">${escapedCode}</code></pre>
        </div>
      `;
    }
  }
});

let sessions: ChatSession[] = [];
let activeSessionId: string = "";
let isSending: boolean = false;
let metricsInterval: number | null = null;

const $ = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id) as T | null;
  if (!el) throw new Error(`Element #${id} not found`);
  return el;
};

const sessionListEl = $<HTMLElement>("session-list");
const chatContainerEl = $<HTMLElement>("chat-container");
const welcomeScreenEl = $<HTMLElement>("welcome-screen");
const welcomeMessageEl = $<HTMLElement>("welcome-message");
const messageInput = $<HTMLTextAreaElement>("message-input");
const sendBtn = $<HTMLButtonElement>("send-btn");
const stopBtn = $<HTMLButtonElement>("stop-btn");
const newSessionBtn = $<HTMLButtonElement>("new-session-btn");
const attachBtn = $<HTMLButtonElement>("attach-btn");
const fileInput = $<HTMLInputElement>("file-input");
const settingsTrigger = $<HTMLButtonElement>("settings-trigger");
const settingsDropdown = $<HTMLElement>("settings-dropdown");
const radiusSlider = $<HTMLInputElement>("radius-slider");
const radiusValue = $<HTMLElement>("radius-value");
const workspacePathEl = $<HTMLElement>("workspace-path");
const memoryBar = $<HTMLElement>("memory-bar");
const memoryValue = $<HTMLElement>("memory-value");
const contextBar = $<HTMLElement>("context-bar");
const contextValue = $<HTMLElement>("context-value");
const agentDot = $<HTMLElement>("agent-dot");
const agentRing = $<HTMLElement>("agent-ring");
const agentStatus = $<HTMLElement>("agent-status");

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

function scrollToBottom(): void {
  chatContainerEl.scrollTop = chatContainerEl.scrollHeight;
}

function persistState(): void {
  saveSessions(sessions, activeSessionId);
}

function getSessionGroup(session: ChatSession): SessionGroup {
  const now = Date.now();
  const ts = session.updatedAt || session.createdAt || 0;
  const diff = now - ts;
  if (diff < 86400000) return "Hoy";
  if (diff < 172800000) return "Ayer";
  if (diff < 604800000) return "Últimos 7 días";
  return "Anterior";
}

const GROUP_ORDER: SessionGroup[] = ["Hoy", "Ayer", "Últimos 7 días", "Anterior"];

function groupSessions(): Map<SessionGroup, ChatSession[]> {
  const groups = new Map<SessionGroup, ChatSession[]>();
  for (const g of GROUP_ORDER) groups.set(g, []);
  for (const s of sessions) {
    const g = getSessionGroup(s);
    const arr = groups.get(g);
    if (arr) arr.push(s); else groups.get("Anterior")!.push(s);
  }
  return groups;
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ── SETTINGS ──
function initSettings(): void {
  const saved = localStorage.getItem("nex_interface_radius");
  if (saved) {
    const v = parseInt(saved);
    radiusSlider.value = String(v);
    document.documentElement.style.setProperty("--interface-radius", v + "px");
    radiusValue.textContent = v + "px";
  }

  settingsTrigger.addEventListener("click", (e) => {
    e.stopPropagation();
    settingsDropdown.classList.toggle("open");
  });

  document.addEventListener("click", (e) => {
    if (!settingsDropdown.contains(e.target as Node) && e.target !== settingsTrigger) {
      settingsDropdown.classList.remove("open");
    }
  });

  radiusSlider.addEventListener("input", () => {
    const v = parseInt(radiusSlider.value);
    document.documentElement.style.setProperty("--interface-radius", v + "px");
    radiusValue.textContent = v + "px";
    localStorage.setItem("nex_interface_radius", String(v));
  });
}

// ── WELCOME ──
function initWelcome(): void {
  welcomeMessageEl.textContent = getRandomWelcomeMessage();
}

function initPlasma(): void {
  const canvas = document.getElementById("plasma-canvas") as HTMLCanvasElement;
  if (canvas) {
    const core = new PlasmaCore(canvas);
    core.start();
  }
}

function showWelcome(): void {
  welcomeScreenEl.style.display = "flex";
  chatContainerEl.style.display = "none";
}

function hideWelcome(): void {
  welcomeScreenEl.style.display = "none";
  chatContainerEl.style.removeProperty("display");
}

// ── SESSIONS ──
function createSession(title?: string): ChatSession {
  const now = Date.now();
  return {
    id: generateId(),
    title: title || `Chat ${sessions.length + 1}`,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

function getActiveSession(): ChatSession | undefined {
  return sessions.find((s) => s.id === activeSessionId);
}

function switchSession(id: string): void {
  activeSessionId = id;
  renderSidebar();
  updateMainView();
  highlightActiveSession();
  messageInput.focus();
  persistState();
}

function addSession(session: ChatSession): void {
  sessions.push(session);
  switchSession(session.id);
}

function deleteSession(id: string): void {
  const index = sessions.findIndex((s) => s.id === id);
  if (index === -1) return;
  sessions.splice(index, 1);
  if (sessions.length === 0) {
    const def = createSession("Chat 1 - General");
    sessions = [def];
    activeSessionId = def.id;
  } else if (activeSessionId === id) {
    const next = Math.min(index, sessions.length - 1);
    activeSessionId = sessions[next].id;
  }
  renderSidebar();
  updateMainView();
  highlightActiveSession();
  persistState();
}

function renameSession(id: string): void {
  const session = sessions.find((s) => s.id === id);
  if (!session) return;
  const newTitle = prompt("Renombrar sesión:", session.title);
  if (newTitle && newTitle.trim() && newTitle.trim() !== session.title) {
    session.title = newTitle.trim();
    renderSidebar();
    updateMainView();
    persistState();
  }
}

// ── RENDER: SIDEBAR ──
function renderSidebar(): void {
  const groups = groupSessions();
  let html = "";
  for (const g of GROUP_ORDER) {
    const items = groups.get(g);
    if (!items || items.length === 0) continue;
    html += `<div class="text-[10px] font-semibold uppercase tracking-[0.08em] text-white/20 px-2 pt-4 pb-1.5 select-none">${g}</div>`;
    for (const s of items) {
      const active = s.id === activeSessionId;
      html += `
        <div class="session-item ${active ? "active" : ""}" data-id="${s.id}">
          <svg class="w-3.5 h-3.5 shrink-0 ${active ? "text-indigo-400/60" : "text-white/20"}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span class="flex-1 truncate">${escapeHtml(s.title)}</span>
          <span class="text-[10px] font-medium ${active ? "text-indigo-400/40" : "text-white/15"}">${s.messages.length}</span>
          <div class="hover-actions">
            <button class="session-action-btn rename-btn" data-id="${s.id}" title="Renombrar">
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            </button>
            <button class="session-action-btn danger delete-btn" data-id="${s.id}" title="Eliminar">
              <svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>`;
    }
  }
  sessionListEl.innerHTML = html || '<div class="text-center text-white/20 text-xs py-8 select-none">Sin sesiones</div>';
}

function highlightActiveSession(): void {
  document.querySelectorAll(".session-item").forEach((el) => {
    el.classList.toggle("active", (el as HTMLElement).dataset.id === activeSessionId);
  });
}

// ── RENDER: MAIN VIEW ──
function updateMainView(): void {
  const session = getActiveSession();
  if (!session || session.messages.length === 0) {
    showWelcome();
    return;
  }
  hideWelcome();
  renderMessages();
}

function renderMessages(): void {
  const session = getActiveSession();
  if (!session || session.messages.length === 0) { showWelcome(); return; }

  chatContainerEl.innerHTML = session.messages
    .map((m, index) => {
      const content = m.role === "assistant" ? renderMarkdown(m.text) : escapeHtml(m.text);
      const avatarSvg = m.role === "assistant"
        ? `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M6.12 9.24a2 2 0 1 1 2.83-2.83l1.41 1.41a2 2 0 1 1-2.83 2.83z"/><path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4H4a2 2 0 0 1-2-2z"/><path d="M9 19a2 2 0 1 1 2.83-2.83l1.41 1.41A2 2 0 1 1 9 19zm8.88-9.76a2 2 0 1 1-2.83-2.83l1.41 1.41a2 2 0 1 1 2.83 2.83z"/><path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-2-2zm-3 7a2 2 0 1 1-2.83 2.83l-1.41-1.41A2 2 0 1 1 13 19z"/></svg>`
        : `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

      const copyBtnHtml = m.role === "assistant"
        ? `<button class="copy-msg-btn" data-index="${index}" title="Copiar respuesta">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
           </button>`
        : "";

      return `
        <div class="message-wrapper ${m.role}">
          <div class="message-avatar ${m.role}">${avatarSvg}</div>
          <div class="message-body">
            <div class="flex items-center justify-between px-0.5">
              <span class="message-sender ${m.role}">${m.role === "assistant" ? "Nex" : "Tú"}</span>
              ${copyBtnHtml}
            </div>
            <div class="message-bubble ${m.role}">${content}</div>
          </div>
        </div>`;
    })
    .join("");

  scrollToBottom();
}

function appendMessage(role: "user" | "assistant", text: string): void {
  const session = getActiveSession();
  if (!session) return;
  session.messages.push({ role, text, timestamp: Date.now() });
  session.updatedAt = Date.now();
  hideWelcome();
  renderMessages();
  renderSidebar();
  persistState();
}

// ── LOADING ──
function showLoading(): void {
  chatContainerEl.insertAdjacentHTML(
    "beforeend",
    `<div class="message-wrapper assistant" id="loading-msg">
      <div class="message-avatar assistant">
        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M6.12 9.24a2 2 0 1 1 2.83-2.83l1.41 1.41a2 2 0 1 1-2.83 2.83z"/><path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4H4a2 2 0 0 1-2-2z"/><path d="M9 19a2 2 0 1 1 2.83-2.83l1.41 1.41A2 2 0 1 1 9 19zm8.88-9.76a2 2 0 1 1-2.83-2.83l1.41 1.41a2 2 0 1 1 2.83 2.83z"/><path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-2-2zm-3 7a2 2 0 1 1-2.83 2.83l-1.41-1.41A2 2 0 1 1 13 19z"/></svg>
      </div>
      <div class="message-body">
        <div class="px-0.5"><span class="message-sender assistant">Nex</span></div>
        <div class="message-bubble loading">
          <span>Pensando</span>
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
          <span class="pulse-dot"></span>
        </div>
      </div>
    </div>`
  );
  scrollToBottom();
}

function removeLoading(): void {
  const el = document.getElementById("loading-msg");
  if (el) el.remove();
}

let streamAbortController: AbortController | null = null;

function showStreamingUI(): HTMLElement {
  removeLoading();
  const wrapper = document.createElement("div");
  wrapper.className = "message-wrapper assistant";
  wrapper.id = "streaming-msg";
  wrapper.innerHTML = `
    <div class="message-avatar assistant">
      <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M6.12 9.24a2 2 0 1 1 2.83-2.83l1.41 1.41a2 2 0 1 1-2.83 2.83z"/><path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4H4a2 2 0 0 1-2-2z"/><path d="M9 19a2 2 0 1 1 2.83-2.83l1.41 1.41A2 2 0 1 1 9 19zm8.88-9.76a2 2 0 1 1-2.83-2.83l1.41 1.41a2 2 0 1 1 2.83 2.83z"/><path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-2-2zm-3 7a2 2 0 1 1-2.83 2.83l-1.41-1.41A2 2 0 1 1 13 19z"/></svg>
    </div>
    <div class="message-body">
      <div class="px-0.5"><span class="message-sender assistant">Nex</span></div>
      <div id="streaming-tools"></div>
      <div class="message-bubble assistant" id="streaming-bubble"></div>
    </div>
  </div>`;
  chatContainerEl.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function addToolCard(tool: string, args: Record<string, unknown>): string {
  const id = "tool-" + Date.now() + "-" + Math.random().toString(36).slice(2, 6);
  const argsPreview = Object.entries(args)
    .filter(([k]) => k !== "workspace_root")
    .map(([k, v]) => `${k}: ${String(v).slice(0, 60)}`)
    .join(", ");

  const container = document.getElementById("streaming-tools");
  if (!container) return id;

  const card = document.createElement("div");
  card.className = "tool-call";
  card.id = id;
  card.innerHTML = `
    <div class="tool-call-header">
      <div class="tool-call-spinner"></div>
      <span class="tool-call-name">${tool}</span>
      <span class="tool-call-status">ejecutando</span>
    </div>
    <div class="tool-call-body">${argsPreview}</div>
  `;
  container.appendChild(card);
  scrollToBottom();
  return id;
}

function updateToolCard(id: string, result: Record<string, unknown>): void {
  const card = document.getElementById(id);
  if (!card) return;
  const header = card.querySelector(".tool-call-header")!;
  const spinner = header.querySelector(".tool-call-spinner")!;
  const status = header.querySelector(".tool-call-status")!;

  const hasError = result && result.error;
  spinner.className = hasError ? "tool-call-spinner" : "";
  spinner.style.display = "none";

  if (hasError) {
    status.className = "tool-call-status tool-call-error";
    status.textContent = "error";
  } else {
    status.className = "tool-call-status tool-call-done";
    status.textContent = "listo";
  }
}

function finalizeStreaming(text: string): void {
  const wrapper = document.getElementById("streaming-msg");
  if (!wrapper) return;
  wrapper.id = "";

  const session = getActiveSession();
  if (session) {
    session.messages.push({ role: "assistant", text, timestamp: Date.now() });
    session.updatedAt = Date.now();
  }

  const bubble = wrapper.querySelector("#streaming-bubble") as HTMLElement;
  if (bubble) {
    bubble.innerHTML = renderMarkdown(text);
    bubble.id = "";
  }
  const tools = document.getElementById("streaming-tools");
  if (tools) tools.id = "";

  renderSidebar();
  persistState();
}

// ── SEND ──
async function sendMessage(): Promise<void> {
  const text = messageInput.value.trim();
  if (!text || isSending) return;
  const session = getActiveSession();
  if (!session) return;

  messageInput.value = "";
  messageInput.style.height = "auto";
  appendMessage("user", text);

  isSending = true;
  sendBtn.disabled = true;
  stopBtn.classList.add("visible");

  streamAbortController = new AbortController();

  let assistantText = "";
  showLoading();

  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: session.id }),
      signal: streamAbortController.signal,
    });

    removeLoading();

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    showStreamingUI();
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        if (!part.trim()) continue;
        const lines = part.split("\n");
        let eventType = "";
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7);
          else if (line.startsWith("data: ")) dataStr = line.slice(6);
        }

        if (!eventType || !dataStr) continue;

        if (eventType === "tool_start") {
          const d = JSON.parse(dataStr);
          addToolCard(d.tool, d.args);
        } else if (eventType === "tool_end") {
          const d = JSON.parse(dataStr);
          const cards = document.querySelectorAll(".tool-call");
          const lastCard = cards[cards.length - 1];
          if (lastCard) updateToolCard(lastCard.id, d.result);
        } else if (eventType === "text") {
          assistantText += JSON.parse(dataStr);
          const bubble = document.getElementById("streaming-bubble");
          if (bubble) bubble.textContent = assistantText;
          scrollToBottom();
        } else if (eventType === "done") {
          finalizeStreaming(assistantText);
        }
      }
    }

    if (assistantText) finalizeStreaming(assistantText);
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    removeLoading();
    const existing = document.getElementById("streaming-msg");
    if (existing) existing.remove();
    const msg = error instanceof Error ? error.message : "Error desconocido";
    appendMessage("assistant", `⚠️ Error al conectar con el backend: ${msg}`);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    stopBtn.classList.remove("visible");
    messageInput.focus();
    streamAbortController = null;
  }
}

function stopExecution(): void {
  if (streamAbortController) {
    streamAbortController.abort();
    streamAbortController = null;
  }
  isSending = false;
  sendBtn.disabled = false;
  stopBtn.classList.remove("visible");
  removeLoading();
  const wrapper = document.getElementById("streaming-msg");
  if (wrapper) wrapper.remove();
}

// ── METRICS ──
async function fetchMetrics(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/metrics`);
    if (!res.ok) return;
    const data: SystemMetrics = await res.json();

    const memPct = Math.min(data.memory, 100);
    memoryBar.style.width = memPct + "%";
    memoryValue.textContent = memPct + "%";

    const ctxPct = Math.min(data.context_buffer, 100);
    contextBar.style.width = ctxPct + "%";
    contextValue.textContent = ctxPct + "%";

    const online = data.agent_status === "online";
    agentDot.className = `agent-dot ${online ? "bg-green-500" : "bg-red-500"}`;
    if (online) {
      agentDot.style.boxShadow = "0 0 10px rgba(34, 197, 94, 0.4)";
    } else {
      agentDot.style.boxShadow = "0 0 10px rgba(239, 68, 68, 0.4)";
    }
    agentRing.setAttribute("stroke", online ? "#22c55e" : "#ef4444");
    agentStatus.textContent = online ? "Online" : data.agent_status === "busy" ? "Ocupado" : "Offline";
    agentStatus.className = `agent-state ${online ? "text-green-400/70" : "text-red-400/70"}`;

    const cpuPct = Math.min(data.cpu, 100);
    const ringOffset = 72.2 - (72.2 * cpuPct) / 100;
    agentRing.style.strokeDashoffset = String(ringOffset);
  } catch {
    // non-critical
  }
}

function initMetrics(): void {
  fetchMetrics();
  metricsInterval = window.setInterval(fetchMetrics, 5000);
}

// ── WORKSPACE ──
async function initWorkspace(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/workspace`);
    if (res.ok) {
      const data: { path: string } = await res.json();
      workspacePathEl.textContent = data.path || "—";
    }
  } catch {
    workspacePathEl.textContent = "—";
  }
}

// ── FILE ATTACH ──
function initFileAttach(): void {
  attachBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      const names = Array.from(fileInput.files).map((f) => f.name).join(", ");
      messageInput.value = messageInput.value
        ? messageInput.value + `\n[Archivos adjuntos: ${names}]`
        : `[Archivos adjuntos: ${names}]`;
      fileInput.value = "";
      messageInput.dispatchEvent(new Event("input"));
      messageInput.focus();
    }
  });
}

// ── MARKDOWN ──
function renderMarkdown(text: string): string {
  return marked.parse(text, { breaks: true }) as string;
}

// ── SPOTLIGHT ──
function openSpotlight(): void {
  const existing = document.getElementById("spotlight-overlay");
  if (existing) {
    existing.classList.add("visible");
    existing.style.display = "flex";
    const input = document.getElementById("spotlight-input") as HTMLInputElement;
    if (input) { input.value = ""; input.focus(); }
    renderSpotlightList("");
    return;
  }
  const overlay = document.createElement("div");
  overlay.id = "spotlight-overlay";
  overlay.innerHTML = `
    <div id="spotlight-modal">
      <input id="spotlight-input" type="text" class="!border-none" placeholder="Buscar o crear sesión..." autocomplete="off" />
      <div id="spotlight-list" class="overflow-y-auto p-2.5 space-y-0.5"></div>
    </div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeSpotlight();
  });
  requestAnimationFrame(() => {
    overlay.style.display = "flex";
    requestAnimationFrame(() => overlay.classList.add("visible"));
    const input = document.getElementById("spotlight-input") as HTMLInputElement;
    if (input) { input.value = ""; input.focus(); }
    renderSpotlightList("");
  });
}

function closeSpotlight(): void {
  const overlay = document.getElementById("spotlight-overlay");
  if (!overlay) return;
  overlay.classList.remove("visible");
  setTimeout(() => { overlay.style.display = "none"; }, 200);
}

function renderSpotlightList(filter: string): void {
  const list = document.getElementById("spotlight-list");
  if (!list) return;
  const q = filter.toLowerCase().trim();
  let items = sessions;
  if (q) {
    items = items.filter(
      (s) => s.title.toLowerCase().includes(q) || s.messages.some((m) => m.text.toLowerCase().includes(q))
    );
  }
  const html = items.map((s) =>
    `<div class="spotlight-item" data-id="${s.id}">
      <span>${escapeHtml(s.title)}</span>
      <span class="text-[11px] text-white/20">${s.messages.length} msgs</span>
    </div>`
  ).join("");

  const createHtml = q
    ? `<div class="spotlight-item" data-action="create">+ Crear sesión: "${escapeHtml(filter.trim())}"</div>`
    : "";

  list.innerHTML = html + createHtml || '<div class="text-white/20 text-sm text-center py-6 select-none">Sin resultados</div>';
}

function handleSpotlightAction(id: string): void {
  closeSpotlight();
  const s = sessions.find((s) => s.id === id);
  if (s) switchSession(id);
}

function handleSpotlightCreate(title: string): void {
  closeSpotlight();
  const session = createSession(title);
  addSession(session);
  renderSidebar();
}

// ── INIT ──
document.addEventListener("DOMContentLoaded", () => {
  const saved = loadSessions();
  if (saved && saved.sessions.length > 0) {
    sessions = saved.sessions;
    activeSessionId = saved.activeId ?? saved.sessions[0].id;
  } else {
    const defaultSession = createSession("Chat 1 - General");
    sessions = [defaultSession];
    activeSessionId = defaultSession.id;
    persistState();
  }

  initWelcome();
  initPlasma();
  initSettings();
  initMetrics();
  initWorkspace();
  initFileAttach();
  renderSidebar();
  updateMainView();

  // Session list delegation
  sessionListEl.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    const deleteBtn = target.closest(".delete-btn") as HTMLElement | null;
    if (deleteBtn && deleteBtn.dataset.id) {
      e.stopPropagation();
      deleteSession(deleteBtn.dataset.id);
      return;
    }
    const renameBtn = target.closest(".rename-btn") as HTMLElement | null;
    if (renameBtn && renameBtn.dataset.id) {
      e.stopPropagation();
      renameSession(renameBtn.dataset.id);
      return;
    }
    const item = target.closest(".session-item") as HTMLElement | null;
    if (item && item.dataset.id) {
      switchSession(item.dataset.id);
    }
  });

  // Chat container delegation (copy buttons)
  chatContainerEl.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    const copyMsgBtn = target.closest(".copy-msg-btn") as HTMLElement | null;
    if (copyMsgBtn) {
      const idx = parseInt(copyMsgBtn.dataset.index || "");
      const session = getActiveSession();
      if (session && !isNaN(idx) && session.messages[idx]) {
        navigator.clipboard.writeText(session.messages[idx].text).then(() => {
          const svg = copyMsgBtn.querySelector("svg");
          if (svg) {
            const original = svg.outerHTML;
            svg.outerHTML = `<svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`;
            setTimeout(() => { copyMsgBtn.innerHTML = original; }, 2000);
          }
        });
      }
      return;
    }
    const copyCodeBtn = target.closest(".copy-code-btn") as HTMLElement | null;
    if (copyCodeBtn) {
      const pre = copyCodeBtn.closest(".code-block-wrapper")?.querySelector("pre code") as HTMLElement | null;
      if (pre) {
        navigator.clipboard.writeText(pre.innerText).then(() => {
          const orig = copyCodeBtn.textContent;
          copyCodeBtn.textContent = "Copiado!";
          copyCodeBtn.classList.add("copied");
          setTimeout(() => {
            copyCodeBtn.textContent = orig;
            copyCodeBtn.classList.remove("copied");
          }, 2000);
        });
      }
    }
  });

  // New session
  newSessionBtn.addEventListener("click", () => {
    const session = createSession();
    addSession(session);
    renderSidebar();
  });

  // Send
  messageInput.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
  });
  sendBtn.addEventListener("click", sendMessage);
  stopBtn.addEventListener("click", stopExecution);

  // ── KEYBOARD SHORTCUTS ──
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      const overlay = document.getElementById("spotlight-overlay");
      if (overlay && overlay.classList.contains("visible")) {
        const first = overlay.querySelector(".spotlight-item") as HTMLElement | null;
        if (first && first.dataset.id) handleSpotlightAction(first.dataset.id);
      } else {
        openSpotlight();
      }
    }
    if (e.key === "Escape") {
      const overlay = document.getElementById("spotlight-overlay");
      if (overlay && overlay.classList.contains("visible")) {
        e.preventDefault();
        closeSpotlight();
      }
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const overlay = document.getElementById("spotlight-overlay");
      if (!overlay || !overlay.classList.contains("visible")) return;
      e.preventDefault();
      const items = overlay.querySelectorAll<HTMLElement>(".spotlight-item");
      if (items.length === 0) return;
      const current = overlay.querySelector<HTMLElement>(".highlighted");
      let idx = -1;
      if (current) {
        current.classList.remove("highlighted");
        idx = Array.from(items).indexOf(current);
      }
      const next = e.key === "ArrowDown"
        ? (idx + 1) % items.length
        : (idx - 1 + items.length) % items.length;
      items[next].classList.add("highlighted");
      items[next].scrollIntoView({ block: "nearest" });
    }
  });

  // Spotlight events
  document.addEventListener("click", (e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(".spotlight-item") as HTMLElement | null;
    if (!target) return;
    const overlay = document.getElementById("spotlight-overlay");
    if (!overlay || !overlay.classList.contains("visible")) return;
    e.preventDefault();
    const input = document.getElementById("spotlight-input") as HTMLInputElement;
    if (target.dataset.action === "create") {
      const title = input?.value.trim() || "";
      if (title) handleSpotlightCreate(title);
    } else if (target.dataset.id) {
      handleSpotlightAction(target.dataset.id);
    }
  });

  document.addEventListener("input", (e: Event) => {
    const input = e.target as HTMLInputElement;
    if (input.id === "spotlight-input") renderSpotlightList(input.value);
  });

  document.addEventListener("keydown", (e: KeyboardEvent) => {
    const input = e.target as HTMLInputElement;
    if (input.id !== "spotlight-input") return;
    if (e.key !== "Enter") return;
    e.preventDefault();
    const overlay = document.getElementById("spotlight-overlay");
    if (!overlay) return;
    const highlighted = overlay.querySelector<HTMLElement>(".highlighted");
    if (highlighted) {
      if (highlighted.dataset.action === "create") {
        handleSpotlightCreate(input.value.trim());
      } else if (highlighted.dataset.id) {
        handleSpotlightAction(highlighted.dataset.id);
      }
      return;
    }
    const first = overlay.querySelector<HTMLElement>(".spotlight-item");
    if (first && first.dataset.id) {
      handleSpotlightAction(first.dataset.id);
    } else if (input.value.trim()) {
      handleSpotlightCreate(input.value.trim());
    }
  });
});
