import type { ChatSession, SessionGroup, Message } from "../types";
import { t } from "../i18n/index";
import { saveSessions } from "./history";
import { $, generateId, escapeHtml } from "./ui";

let sessions: ChatSession[] = [];
let activeSessionId: string = "";

const sessionListEl = $<HTMLElement>("session-list");
const chatContainerEl = $<HTMLElement>("chat-container");
const welcomeScreenEl = $<HTMLElement>("welcome-screen");

function getSessionGroup(session: ChatSession): SessionGroup {
  const now = Date.now();
  const ts = session.updatedAt || session.createdAt || 0;
  const diff = now - ts;
  if (diff < 86400000) return "today";
  if (diff < 172800000) return "yesterday";
  if (diff < 604800000) return "last7";
  return "older";
}

function groupLabel(group: SessionGroup): string {
  const map: Record<SessionGroup, string> = {
    today: t("sidebar.today", "Today"),
    yesterday: t("sidebar.yesterday", "Yesterday"),
    last7: t("sidebar.last7Days", "Last 7 days"),
    older: t("sidebar.older", "Older"),
  };
  return map[group];
}

const GROUP_ORDER: SessionGroup[] = ["today", "yesterday", "last7", "older"];

function groupSessions(): Map<SessionGroup, ChatSession[]> {
  const groups = new Map<SessionGroup, ChatSession[]>();
  for (const g of GROUP_ORDER) groups.set(g, []);
  for (const s of sessions) {
    const g = getSessionGroup(s);
    const arr = groups.get(g);
    if (arr) arr.push(s); else groups.get("older")!.push(s);
  }
  return groups;
}

function persistState(): void {
  saveSessions(sessions, activeSessionId);
}

export { persistState };

export function showWelcome(): void {
  welcomeScreenEl.style.display = "flex";
  chatContainerEl.style.display = "none";
}

export function hideWelcome(): void {
  welcomeScreenEl.style.display = "none";
  chatContainerEl.style.removeProperty("display");
}

export function getSessions(): ChatSession[] {
  return sessions;
}

export function setSessions(newSessions: ChatSession[], activeId: string): void {
  sessions = newSessions;
  activeSessionId = activeId;
}

export function getActiveSession(): ChatSession | undefined {
  return sessions.find((s) => s.id === activeSessionId);
}

export function getActiveSessionId(): string {
  return activeSessionId;
}

export function createSession(title?: string): ChatSession {
  const now = Date.now();
  return {
    id: generateId(),
    title: title || `Chat ${sessions.length + 1}`,
    messages: [],
    createdAt: now,
    updatedAt: now,
  };
}

export function addSession(session: ChatSession): void {
  sessions.push(session);
  switchSession(session.id);
}

export function switchSession(id: string): void {
  activeSessionId = id;
  renderSidebar();
  highlightActiveSession();
  persistState();
}

export function deleteSession(id: string): void {
  const confirmDel = (document.getElementById("setting-confirm-delete") as HTMLInputElement)?.checked;
  if (confirmDel !== false) {
    const session = sessions.find((s) => s.id === id);
    const title = session?.title || "this session";
    if (!confirm(`Delete "${title}"?`)) return;
  }
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
  highlightActiveSession();
  persistState();
}

export function renameSession(id: string): void {
  const session = sessions.find((s) => s.id === id);
  if (!session) return;
  const newTitle = prompt(t("sidebar.rename", "Rename session") + ":", session.title);
  if (newTitle && newTitle.trim() && newTitle.trim() !== session.title) {
    session.title = newTitle.trim();
    renderSidebar();
    persistState();
  }
}

export function renderSidebar(): void {
  const groups = groupSessions();
  let html = "";
  for (const g of GROUP_ORDER) {
    const items = groups.get(g);
    if (!items || items.length === 0) continue;
    html += `<div class="text-[10px] font-semibold uppercase tracking-[0.08em] text-white/20 px-2 pt-4 pb-1.5 select-none">${groupLabel(g)}</div>`;
    for (const s of items) {
      const active = s.id === activeSessionId;
      html += `
        <div class="session-item ${active ? "active" : ""}" data-id="${s.id}">
          <svg class="w-3.5 h-3.5 shrink-0 ${active ? "accent-text-60" : "text-white/20"}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          <span class="flex-1 truncate">${escapeHtml(s.title)}</span>
          <span class="text-[10px] font-medium ${active ? "accent-text-40" : "text-white/15"}">${s.messages.length}</span>
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
  sessionListEl.innerHTML = html || `<div class="text-center text-white/20 text-xs py-8 select-none">${t("sidebar.noSessions", "No sessions")}</div>`;
}

function highlightActiveSession(): void {
  document.querySelectorAll(".session-item").forEach((el) => {
    el.classList.toggle("active", (el as HTMLElement).dataset.id === activeSessionId);
  });
}

export function updateMainView(): void {
  const session = getActiveSession();
  if (!session || session.messages.length === 0) {
    showWelcome();
    return;
  }
  hideWelcome();
}
