import type { ChatSession } from "../types";

const STORAGE_KEY = "nex_sessions";

export function saveSessions(sessions: ChatSession[], activeId: string): void {
  try {
    const data = { sessions, activeId, updatedAt: Date.now() };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // localStorage lleno o no disponible — ignorar
  }
}

export function loadSessions(): {
  sessions: ChatSession[];
  activeId: string | null;
} | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (!data.sessions || !Array.isArray(data.sessions)) return null;
    return { sessions: data.sessions, activeId: data.activeId ?? null };
  } catch {
    return null;
  }
}
