import { marked } from "marked";
import { saveSessions, loadSessions } from "./renderer/history";
import { PlasmaCore } from "./renderer/plasma-core";
import { t, getRandomWelcomeEntry, initI18n, setLocale, applyTranslationsToDOM, getLocale } from "./i18n/index";
import type { Locale } from "./i18n/locales";

import { $, generateId } from "./renderer/ui";
import { API_BASE } from "./renderer/api";
import { initSettings } from "./renderer/settings";
import {
  getSessions, setSessions, getActiveSession, getActiveSessionId,
  createSession, addSession, deleteSession, renameSession,
  switchSession, renderSidebar, updateMainView, showWelcome, hideWelcome,
} from "./renderer/sessions";
import { sendMessage, stopExecution, renderMessages, appendMessage } from "./renderer/chat";
import { openSpotlight, closeSpotlight } from "./renderer/spotlight";
import { initWatch } from "./renderer/watch";

const chatContainerEl = $<HTMLElement>("chat-container");
const messageInput = $<HTMLTextAreaElement>("message-input");
const sendBtn = $<HTMLButtonElement>("send-btn");
const stopBtn = $<HTMLButtonElement>("stop-btn");
const newSessionBtn = $<HTMLButtonElement>("new-session-btn");
const attachBtn = $<HTMLButtonElement>("attach-btn");
const fileInput = $<HTMLInputElement>("file-input");
const settingsTrigger = $<HTMLButtonElement>("settings-trigger");
const sessionListEl = $<HTMLElement>("session-list");
const workspacePathEl = $<HTMLElement>("workspace-path");
const memoryBar = $<HTMLElement>("memory-bar");
const memoryValue = $<HTMLElement>("memory-value");
const contextBar = $<HTMLElement>("context-bar");
const contextValue = $<HTMLElement>("context-value");
const agentDot = $<HTMLElement>("agent-dot");
const agentRing = $<HTMLElement>("agent-ring");
const agentStatus = $<HTMLElement>("agent-status");

// ── WELCOME ──
let welcomeTypingTimer: ReturnType<typeof setTimeout> | null = null;

function initWelcome(): void {
  typeWelcomeMessage(getRandomWelcomeEntry());
}

function typeWelcomeMessage(entry: { message: string; subtitle: string }): void {
  const textEl = document.getElementById("welcome-text")!;
  const subtitleEl = document.getElementById("welcome-subtitle")!;
  const cursorEl = document.getElementById("welcome-cursor")!;
  const quickActions = document.getElementById("quick-actions")!;

  quickActions.classList.remove("visible");
  textEl.textContent = "";
  subtitleEl.textContent = "";
  cursorEl.style.display = "inline-block";
  messageInput.focus();

  let charIndex = 0;
  const typeSpeed = 35 + Math.random() * 20;

  function typeChar() {
    if (charIndex < entry.message.length) {
      textEl.textContent += entry.message[charIndex];
      charIndex++;
      welcomeTypingTimer = setTimeout(typeChar, typeSpeed);
    } else {
      cursorEl.style.display = "none";
      setTimeout(() => {
        subtitleEl.textContent = entry.subtitle;
        subtitleEl.style.opacity = "0";
        requestAnimationFrame(() => {
          subtitleEl.style.transition = "opacity 0.6s ease";
          subtitleEl.style.opacity = "1";
        });
      }, 300);
      setTimeout(() => { quickActions.classList.add("visible"); }, 1000);
    }
  }
  typeChar();
}

function changeWelcomeMessage(): void {
  const entry = getRandomWelcomeEntry();
  typeWelcomeMessage(entry);
}

// ── PLASMA ──
function initPlasma(): void {
  const canvas = document.getElementById("plasma-canvas") as HTMLCanvasElement;
  if (canvas) {
    const core = new PlasmaCore(canvas);
    core.start();
  }
}

// ── METRICS ──
let metricsInterval: number | null = null;

async function fetchMetrics(): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/metrics`);
    if (!res.ok) return;
    const data: any = await res.json();
    const memPct = Math.min(data.memory, 100);
    memoryBar.style.width = memPct + "%";
    memoryValue.textContent = memPct + "%";
    const ctxPct = Math.min(data.context_buffer, 100);
    contextBar.style.width = ctxPct + "%";
    contextValue.textContent = ctxPct + "%";
    const online = data.agent_status === "online";
    agentDot.className = `agent-dot ${online ? "bg-green-500" : "bg-red-500"}`;
    agentDot.style.boxShadow = online ? "0 0 10px rgba(34, 197, 94, 0.4)" : "0 0 10px rgba(239, 68, 68, 0.4)";
    agentRing.setAttribute("stroke", online ? "#22c55e" : "#ef4444");
    agentStatus.textContent = online ? "Online" : data.agent_status === "busy" ? "Ocupado" : "Offline";
    agentStatus.className = `agent-state ${online ? "text-green-400/70" : "text-red-400/70"}`;
    const cpuPct = Math.min(data.cpu, 100);
    const ringOffset = 72.2 - (72.2 * cpuPct) / 100;
    agentRing.style.strokeDashoffset = String(ringOffset);
  } catch {}
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
function uploadImage(file: File): Promise<void> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const b64 = result.split(",")[1];
      setImagePreview(b64, file.type, file.name);
      resolve();
    };
    reader.readAsDataURL(file);
  });
}

function initFileAttach(): void {
  attachBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files && fileInput.files.length > 0) {
      const files = Array.from(fileInput.files);
      const images = files.filter((f) => f.type.startsWith("image/"));
      const others = files.filter((f) => !f.type.startsWith("image/"));
      if (images.length > 0) handleImageFile(images[0]);
      if (others.length > 0) {
        const names = others.map((f) => f.name).join(", ");
        messageInput.value = messageInput.value
          ? messageInput.value + `\n[${t("fileAttach.files", "Files")}: ${names}]`
          : `[${t("fileAttach.files", "Files")}: ${names}]`;
      }
      fileInput.value = "";
      messageInput.dispatchEvent(new Event("input"));
      messageInput.focus();
    }
  });
}

function setImagePreview(data: string, mime: string, filename: string): void {
  const container = document.getElementById("image-preview")!;
  container.innerHTML = `
    <div class="preview-thumb">
      <img src="data:${mime};base64,${data}" alt="${filename}" />
      <button class="remove-preview" title="Quitar imagen">&times;</button>
    </div>
  `;
  container.classList.remove("hidden");
  container.querySelector(".remove-preview")!.addEventListener("click", clearImagePreview);
  (window as any).__pendingImage = { data, mime, filename };
}

function clearImagePreview(): void {
  const container = document.getElementById("image-preview")!;
  container.classList.add("hidden");
  container.innerHTML = "";
  delete (window as any).__pendingImage;
}

function handleImageFile(file: File): void {
  const reader = new FileReader();
  reader.onload = () => {
    const result = reader.result as string;
    const b64 = result.split(",")[1];
    setImagePreview(b64, file.type, file.name);
  };
  reader.readAsDataURL(file);
}

function initDragDrop(): void {
  const inputBar = document.getElementById("input-bar")!;
  inputBar.addEventListener("dragover", (e) => { e.preventDefault(); e.stopPropagation(); inputBar.classList.add("drag-over"); });
  inputBar.addEventListener("dragleave", (e) => { e.preventDefault(); e.stopPropagation(); inputBar.classList.remove("drag-over"); });
  inputBar.addEventListener("drop", (e) => {
    e.preventDefault(); e.stopPropagation();
    inputBar.classList.remove("drag-over");
    const files = e.dataTransfer?.files;
    if (!files || files.length === 0) return;
    for (const file of Array.from(files)) {
      if (file.type.startsWith("image/")) { handleImageFile(file); break; }
    }
  });
}

function initPasteImage(): void {
  messageInput.addEventListener("paste", (e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of Array.from(items)) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) handleImageFile(file);
        break;
      }
    }
  });
}

// ── INIT ──
document.addEventListener("DOMContentLoaded", () => {
  const saved = loadSessions();
  if (saved && saved.sessions.length > 0) {
    setSessions(saved.sessions, saved.activeId ?? saved.sessions[0].id);
  } else {
    const defaultSession = createSession("Chat 1 - General");
    setSessions([defaultSession], defaultSession.id);
  }

  initWelcome();
  initPlasma();
  initSettings();
  initMetrics();
  initWorkspace();
  initWatch();
  initFileAttach();
  initDragDrop();
  initPasteImage();
  renderSidebar();
  updateMainView();

  sessionListEl.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    const deleteBtn = target.closest(".delete-btn") as HTMLElement | null;
    if (deleteBtn?.dataset.id) { e.stopPropagation(); deleteSession(deleteBtn.dataset.id); return; }
    const renameBtn = target.closest(".rename-btn") as HTMLElement | null;
    if (renameBtn?.dataset.id) { e.stopPropagation(); renameSession(renameBtn.dataset.id); return; }
    const item = target.closest(".session-item") as HTMLElement | null;
    if (item?.dataset.id) switchSession(item.dataset.id);
  });

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
          setTimeout(() => { copyCodeBtn.textContent = orig; copyCodeBtn.classList.remove("copied"); }, 2000);
        });
      }
    }
  });

  document.getElementById("quick-actions")?.addEventListener("click", (e: MouseEvent) => {
    const btn = (e.target as HTMLElement).closest(".quick-action-btn") as HTMLElement | null;
    if (!btn) return;
    if (btn.dataset.action === "settings") { settingsTrigger.click(); return; }
    const hint = t(`welcome.quickActions.${btn.dataset.action}Hint` as any, "");
    if (hint) { messageInput.value = hint; messageInput.dispatchEvent(new Event("input")); messageInput.focus(); }
  });

  newSessionBtn.addEventListener("click", () => {
    const session = createSession();
    addSession(session);
    renderSidebar();
  });

  messageInput.addEventListener("keydown", (e: KeyboardEvent) => {
    const sendMode = (document.getElementById("setting-send-mode") as HTMLSelectElement)?.value || "enter";
    const isEnter = e.key === "Enter";
    const withMod = (sendMode === "ctrl_enter" && (e.ctrlKey || e.metaKey)) ||
                    (sendMode === "shift_enter" && e.shiftKey) ||
                    (sendMode === "enter" && !e.shiftKey);
    if (isEnter && withMod) { e.preventDefault(); sendMessage(); }
  });
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 160) + "px";
  });
  sendBtn.addEventListener("click", sendMessage);
  stopBtn.addEventListener("click", stopExecution);

  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      const overlay = document.getElementById("spotlight-overlay");
      if (overlay && overlay.classList.contains("visible")) {
        const first = overlay.querySelector(".spotlight-item") as HTMLElement | null;
        if (first?.dataset.id) { closeSpotlight(); switchSession(first.dataset.id); }
      } else {
        openSpotlight();
      }
    }
    if (e.key === "Escape") {
      const overlay = document.getElementById("spotlight-overlay");
      if (overlay && overlay.classList.contains("visible")) { e.preventDefault(); closeSpotlight(); }
    }
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      const overlay = document.getElementById("spotlight-overlay");
      if (!overlay || !overlay.classList.contains("visible")) return;
      e.preventDefault();
      const items = overlay.querySelectorAll<HTMLElement>(".spotlight-item");
      if (items.length === 0) return;
      const current = overlay.querySelector<HTMLElement>(".highlighted");
      let idx = -1;
      if (current) { current.classList.remove("highlighted"); idx = Array.from(items).indexOf(current); }
      const next = e.key === "ArrowDown" ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length;
      items[next].classList.add("highlighted");
      items[next].scrollIntoView({ block: "nearest" });
    }
  });

  document.addEventListener("click", (e: MouseEvent) => {
    const target = (e.target as HTMLElement).closest(".spotlight-item") as HTMLElement | null;
    if (!target) return;
    const overlay = document.getElementById("spotlight-overlay");
    if (!overlay || !overlay.classList.contains("visible")) return;
    e.preventDefault();
    const input = document.getElementById("spotlight-input") as HTMLInputElement;
    if (target.dataset.action === "create") {
      const title = input?.value.trim() || "";
      if (title) { closeSpotlight(); const s = createSession(title); addSession(s); renderSidebar(); }
    } else if (target.dataset.id) {
      closeSpotlight(); switchSession(target.dataset.id);
    }
  });

  document.addEventListener("input", (e: Event) => {
    const input = e.target as HTMLInputElement;
    if (input.id === "spotlight-input") {
      const list = document.getElementById("spotlight-list");
      if (!list) return;
      const q = input.value.toLowerCase().trim();
      const sessions = getSessions();
      let items = q ? sessions.filter((s) => s.title.toLowerCase().includes(q) || s.messages.some((m) => m.text.toLowerCase().includes(q))) : sessions;
      const html = items.map((s) =>
        `<div class="spotlight-item" data-id="${s.id}"><span>${s.title}</span><span class="text-[11px] text-white/20">${s.messages.length} msgs</span></div>`
      ).join("");
      const createHtml = q ? `<div class="spotlight-item" data-action="create">+ ${t("spotlight.create", "Create session")}: "${input.value.trim()}"</div>` : "";
      list.innerHTML = html + createHtml || `<div class="text-white/20 text-sm text-center py-6 select-none">${t("common.noResults", "No results")}</div>`;
    }
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
      if (highlighted.dataset.action === "create") { closeSpotlight(); const s = createSession(input.value.trim()); addSession(s); renderSidebar(); }
      else if (highlighted.dataset.id) { closeSpotlight(); switchSession(highlighted.dataset.id); }
      return;
    }
    const first = overlay.querySelector<HTMLElement>(".spotlight-item");
    if (first?.dataset.id) { closeSpotlight(); switchSession(first.dataset.id); }
    else if (input.value.trim()) { closeSpotlight(); const s = createSession(input.value.trim()); addSession(s); renderSidebar(); }
  });
});
