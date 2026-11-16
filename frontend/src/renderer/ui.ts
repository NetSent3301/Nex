export const $ = <T extends HTMLElement>(id: string): T => {
  const el = document.getElementById(id) as T | null;
  if (!el) throw new Error(`Element #${id} not found`);
  return el;
};

export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

export function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

export function sanitizeHtml(html: string): string {
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/on\w+\s*=\s*"[^"]*"/gi, "")
    .replace(/on\w+\s*=\s*'[^']*'/gi, "");
}

export function setSelect(id: string, value: any): void {
  const el = document.getElementById(id) as HTMLSelectElement;
  if (el && value != null) el.value = String(value);
}

export function setInput(id: string, value: any): void {
  const el = document.getElementById(id) as HTMLInputElement;
  if (el && value != null) el.value = String(value);
}

export function setCheck(id: string, value: any): void {
  const el = document.getElementById(id) as HTMLInputElement;
  if (el) el.checked = value !== false;
}
