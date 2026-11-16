import { t } from "../i18n/index";
import { escapeHtml } from "./ui";
import { getSessions, getActiveSessionId, switchSession, createSession, addSession, renderSidebar } from "./sessions";

export function openSpotlight(): void {
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
      <input id="spotlight-input" type="text" class="!border-none" placeholder="${t("spotlight.placeholder", "Search or create session...")}" autocomplete="off" />
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

export function closeSpotlight(): void {
  const overlay = document.getElementById("spotlight-overlay");
  if (!overlay) return;
  overlay.classList.remove("visible");
  setTimeout(() => { overlay.style.display = "none"; }, 200);
}

function renderSpotlightList(filter: string): void {
  const list = document.getElementById("spotlight-list");
  if (!list) return;
  const q = filter.toLowerCase().trim();
  let items = getSessions();
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
    ? `<div class="spotlight-item" data-action="create">+ ${t("spotlight.create", "Create session")}: "${escapeHtml(filter.trim())}"</div>`
    : "";

  list.innerHTML = html + createHtml || `<div class="text-white/20 text-sm text-center py-6 select-none">${t("common.noResults", "No results")}</div>`;
}

function handleSpotlightAction(id: string): void {
  closeSpotlight();
  const s = getSessions().find((s) => s.id === id);
  if (s) switchSession(id);
}

function handleSpotlightCreate(title: string): void {
  closeSpotlight();
  const session = createSession(title);
  addSession(session);
  renderSidebar();
}
