import { i18n } from "@lingui/core";
import { detect, fromStorage } from "@lingui/detect-locale";
import { LOCALE_STORAGE_KEY, type Locale, resolveLocale, sourceLocale } from "./locales";

export * from "./locales";
export { i18n };

/**
 * The locale to start in: a previously saved choice from local storage, `sourceLocale` otherwise (Dutch).
 */
export function detectLocale(): Locale {
   try {
      return resolveLocale(detect(fromStorage(LOCALE_STORAGE_KEY)));
   } catch {
      // Sandboxed iframes throw on any localStorage access, before the app has rendered anything at all.
      return resolveLocale(null);
   }
}

/**
 * Loads and activates a catalogue. The import specifier must stay a template
 * literal: that is what lets Vite emit one lazily loaded chunk per locale, so a
 * visitor only downloads the language they are actually reading.
 */
export async function loadCatalog(locale: Locale): Promise<void> {
   try {
      const { messages } = await import(`../locales/${locale}/messages.po`);
      i18n.loadAndActivate({ locale, messages });
   } catch (error) {
      console.error(`Catalog for "${locale}" failed to load, falling back to "${sourceLocale}"`, error);
      const { messages } = await import(`../locales/${sourceLocale}/messages.po`);
      i18n.loadAndActivate({ locale: sourceLocale, messages });
   }
   document.documentElement.lang = i18n.locale;
}

export function saveLocale(locale: Locale): void {
   try {
      localStorage.setItem(LOCALE_STORAGE_KEY, locale);
   } catch {
      // Sandboxed iframe: the choice simply does not survive a reload.
   }
}
