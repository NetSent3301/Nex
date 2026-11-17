import { marked } from "marked";
import { t } from "../i18n/index";
import { API_BASE } from "./api";
import { $, escapeHtml, sanitizeHtml } from "./ui";
import {
  getActiveSession, getActiveSessionId, getSessions,
  renderSidebar, showWelcome, hideWelcome, persistState,
} from "./sessions";
import { emitOrb } from "./orb-engine";

const chatContainerEl = $<HTMLElement>("chat-container");
const messageInput = $<HTMLTextAreaElement>("message-input");
const sendBtn = $<HTMLButtonElement>("send-btn");
const stopBtn = $<HTMLButtonElement>("stop-btn");

let isSending: boolean = false;
let streamAbortController: AbortController | null = null;

function scrollToBottom(): void {
  chatContainerEl.scrollTop = chatContainerEl.scrollHeight;
}

export function renderMessages(): void {
  const session = getActiveSession();
  if (!session || session.messages.length === 0) { showWelcome(); return; }

  chatContainerEl.innerHTML = session.messages
    .map((m, index) => {
      let content = m.role === "assistant" ? renderMarkdown(m.text) : escapeHtml(m.text);
      if (m.image_data && m.image_mime) {
        const imgHtml = `<img class="msg-image" src="data:${m.image_mime};base64,${m.image_data}" alt="attached image" />`;
        content = m.text.trim() ? content + imgHtml : imgHtml;
      }
      const avatarSvg = m.role === "assistant"
        ? `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M6.12 9.24a2 2 0 1 1 2.83-2.83l1.41 1.41a2 2 0 1 1-2.83 2.83z"/><path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4H4a2 2 0 0 1-2-2z"/><path d="M9 19a2 2 0 1 1 2.83-2.83l1.41 1.41A2 2 0 1 1 9 19zm8.88-9.76a2 2 0 1 1-2.83-2.83l1.41 1.41a2 2 0 1 1 2.83 2.83z"/><path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-2-2zm-3 7a2 2 0 1 1-2.83 2.83l-1.41-1.41A2 2 0 1 1 13 19z"/></svg>`
        : `<svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

      const copyBtnHtml = m.role === "assistant"
        ? `<button class="copy-msg-btn" data-index="${index}" title="${t("chat.copyResponse", "Copy response")}">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
           </button>`
        : "";

      return `
        <div class="message-wrapper ${m.role}">
          <div class="message-avatar ${m.role}">${avatarSvg}</div>
          <div class="message-body">
            <div class="flex items-center justify-between px-0.5">
              <span class="message-sender ${m.role}">${m.role === "assistant" ? t("chat.nex", "Nex") : t("chat.you", "You")}</span>
              ${copyBtnHtml}
            </div>
            <div class="message-bubble ${m.role}">${content}</div>
          </div>
        </div>`;
    })
    .join("");

  scrollToBottom();
}

export function appendMessage(role: "user" | "assistant", text: string, imageData?: string, imageMime?: string): void {
  const session = getActiveSession();
  if (!session) return;
  session.messages.push({ role, text, timestamp: Date.now(), image_data: imageData, image_mime: imageMime });
  session.updatedAt = Date.now();
  hideWelcome();
  renderMessages();
  renderSidebar();
  persistState();
}

function showLoading(): void {
  chatContainerEl.insertAdjacentHTML(
    "beforeend",
    `<div class="message-wrapper assistant" id="loading-msg">
      <div class="message-avatar assistant">
        <svg class="w-[17px] h-[17px]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M6.12 9.24a2 2 0 1 1 2.83-2.83l1.41 1.41a2 2 0 1 1-2.83 2.83z"/><path d="M2 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4H4a2 2 0 0 1-2-2z"/><path d="M9 19a2 2 0 1 1 2.83-2.83l1.41 1.41A2 2 0 1 1 9 19zm8.88-9.76a2 2 0 1 1-2.83-2.83l1.41 1.41a2 2 0 1 1 2.83 2.83z"/><path d="M16 12a2 2 0 0 1 2-2h2a2 2 0 0 1 0 4h-2a2 2 0 0 1-2-2zm-3 7a2 2 0 1 1-2.83 2.83l-1.41-1.41A2 2 0 1 1 13 19z"/></svg>
      </div>
      <div class="message-body">
        <div class="px-0.5"><span class="message-sender assistant">${t("chat.nex", "Nex")}</span></div>
        <div class="message-bubble loading">
          <span>${t("chat.thinking", "Thinking")}</span>
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
      <div class="px-0.5"><span class="message-sender assistant">${t("chat.nex", "Nex")}</span></div>
      <div id="streaming-tools"></div>
      <div class="message-bubble assistant" id="streaming-bubble"></div>
    </div>
  </div>`;
  chatContainerEl.appendChild(wrapper);
  scrollToBottom();
  return wrapper;
}

function addToolCard(tool: string, args: Record<string, unknown>, description?: string): string {
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
      <span class="tool-call-status">${t("tool.running", "running")}</span>
    </div>
    ${description ? `<div class="tool-call-why">💡 ${description}</div>` : ""}
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
  const spinner = header.querySelector(".tool-call-spinner") as HTMLElement;
  const status = header.querySelector(".tool-call-status") as HTMLElement;

  const hasError = result && result.error;
  spinner.className = "tool-call-spinner";
  spinner.style.display = "none";

  if (hasError) {
    status.className = "tool-call-status tool-call-error";
    status.textContent = t("tool.error", "error");
  } else {
    status.className = "tool-call-status tool-call-done";
    status.textContent = t("tool.done", "done");
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

export async function sendMessage(): Promise<void> {
  const text = messageInput.value.trim();
  if (!text || isSending) return;
  const session = getActiveSession();
  if (!session) return;

  messageInput.value = "";
  messageInput.style.height = "auto";

  const pendingImage = (window as any).__pendingImage as { data: string; mime: string; filename: string } | undefined;
  const imgData = pendingImage?.data;
  const imgMime = pendingImage?.mime;
  clearImagePreview();

  appendMessage("user", text, imgData, imgMime);

  const autoTitle = (document.getElementById("setting-auto-title") as HTMLInputElement)?.checked;
  if (autoTitle !== false && /^Chat\s+\d+/.test(session.title)) {
    const title = text.slice(0, 50).replace(/\n/g, " ");
    session.title = title + (text.length > 50 ? "..." : "");
    renderSidebar();
    persistState();
  }

  isSending = true;
  emitOrb("send");
  sendBtn.disabled = true;
  stopBtn.classList.add("visible");

  streamAbortController = new AbortController();

  let assistantText = "";
  showLoading();

  const body: Record<string, unknown> = { message: text, session_id: session.id };

  const providerSelect = document.getElementById("setting-provider") as HTMLSelectElement;
  const modelSelect = document.getElementById("setting-model") as HTMLSelectElement;
  const langSelect = document.getElementById("setting-language") as HTMLSelectElement;
  if (providerSelect?.value) body.provider = providerSelect.value;
  if (modelSelect?.value) body.model = modelSelect.value;
  if (langSelect?.value) body.language = langSelect.value;

  if (imgData && imgMime) {
    body.image_data = imgData;
    body.image_mime = imgMime;
  }

  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
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
          emitOrb("tool_start", { tool: d.tool });
          addToolCard(d.tool, d.args, d.description);
        } else if (eventType === "tool_end") {
          const d = JSON.parse(dataStr);
          emitOrb("tool_end", { ok: !(d.result && d.result.error) });
          const cards = document.querySelectorAll(".tool-call");
          const lastCard = cards[cards.length - 1];
          if (lastCard) updateToolCard(lastCard.id, d.result);
        } else if (eventType === "text") {
          const chunk = JSON.parse(dataStr);
          emitOrb("text", { chars: chunk.length });
          assistantText += chunk;
          const bubble = document.getElementById("streaming-bubble");
          if (bubble) bubble.textContent = assistantText;
          scrollToBottom();
        } else if (eventType === "done") {
          emitOrb("done");
          finalizeStreaming(assistantText);
        }
      }
    }

    if (assistantText) {
      emitOrb("done");
      finalizeStreaming(assistantText);
    }
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") return;
    emitOrb("error");
    removeLoading();
    const existing = document.getElementById("streaming-msg");
    if (existing) existing.remove();
    const msg = error instanceof Error ? error.message : "Error desconocido";
    appendMessage("assistant", `${t("chat.errorPrefix", "⚠️ Error connecting to backend")}: ${msg}`);
  } finally {
    isSending = false;
    sendBtn.disabled = false;
    stopBtn.classList.remove("visible");
    messageInput.focus();
    streamAbortController = null;
  }
}

export function stopExecution(): void {
  if (streamAbortController) {
    streamAbortController.abort();
    streamAbortController = null;
  }
  emitOrb("stop");
  isSending = false;
  sendBtn.disabled = false;
  stopBtn.classList.remove("visible");
  removeLoading();
  const wrapper = document.getElementById("streaming-msg");
  if (wrapper) wrapper.remove();
}

function clearImagePreview(): void {
  const container = document.getElementById("image-preview")!;
  container.classList.add("hidden");
  container.innerHTML = "";
  delete (window as any).__pendingImage;
}

function renderMarkdown(text: string): string {
  const raw = marked.parse(text) as string;
  return sanitizeHtml(raw);
}
