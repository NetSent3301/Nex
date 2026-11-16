import { locales, localeList } from "./translations";
import type { Locale, LocaleStrings, WelcomeEntry } from "./locales";

type NestedKeyOf<T> = T extends object
  ? { [K in keyof T]: K extends string
    ? T[K] extends object
      ? `${K}.${NestedKeyOf<T[K]>}`
      : K
    : never
  }[keyof T]
  : never;

type TranslationKey = NestedKeyOf<LocaleStrings>;

let currentLocale: Locale = "en";
let currentStrings: LocaleStrings = locales.en;
let changeListeners: Array<(locale: Locale) => void> = [];

function resolveKey(obj: any, path: string): any {
  return path.split(".").reduce((acc, part) => {
    if (acc == null) return undefined;
    if (Array.isArray(acc) && /^\d+$/.test(part)) return acc[parseInt(part)];
    return acc[part];
  }, obj);
}

export function t(key: TranslationKey, fallback?: string): string {
  const value = resolveKey(currentStrings, key);
  if (typeof value === "string") return value;
  if (fallback !== undefined) return fallback;
  return key;
}

export function getWelcomeEntries(): WelcomeEntry[] {
  return currentStrings.welcome.entries;
}

export function getRandomWelcomeEntry(): WelcomeEntry {
  const entries = currentStrings.welcome.entries;
  const index = Math.floor(Math.random() * entries.length);
  return entries[index];
}

export function getLocale(): Locale {
  return currentLocale;
}

export function getLabel(locale: Locale): string {
  return locales[locale]?.label ?? locale;
}

export function getAllLocales(): Locale[] {
  return localeList;
}

export function autoDetectLocale(): Locale {
  try {
    const lang = navigator.language?.split("-")[0]?.toLowerCase() as Locale;
    if (localeList.includes(lang)) return lang;
    const full = navigator.language?.toLowerCase() as Locale;
    if (localeList.includes(full)) return full;
  } catch {}
  return "en";
}

export function setLocale(locale: Locale): void {
  currentLocale = locale;
  currentStrings = locales[locale] ?? locales.en;
  document.documentElement.lang = locale;
  changeListeners.forEach((fn) => fn(locale));
}

export function onLocaleChange(fn: (locale: Locale) => void): () => void {
  changeListeners.push(fn);
  return () => {
    changeListeners = changeListeners.filter((f) => f !== fn);
  };
}

export function applyTranslationsToDOM(): void {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n") as TranslationKey;
    if (!key) return;
    const isHtml = el.hasAttribute("data-i18n-html");
    const value = resolveKey(currentStrings, key);
    if (typeof value === "string") {
      if (isHtml) {
        el.innerHTML = value;
      } else {
        el.textContent = value;
      }
    }
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder") as TranslationKey;
    if (!key) return;
    const value = resolveKey(currentStrings, key);
    if (typeof value === "string") {
      (el as HTMLInputElement).placeholder = value;
    }
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.getAttribute("data-i18n-title") as TranslationKey;
    if (!key) return;
    const value = resolveKey(currentStrings, key);
    if (typeof value === "string") {
      el.setAttribute("title", value);
    }
  });
}

export function initI18n(preferredLocale?: Locale): Locale {
  const detected = autoDetectLocale();
  const initial = preferredLocale ?? detected;
  setLocale(initial);
  return initial;
}
