import { i18n } from "@lingui/core";
import { detect, fromStorage } from "@lingui/detect-locale";
import { LOCALE_STORAGE_KEY, type Locale, resolveLocale, sourceLocale } from "./locales";

export * from "./locales";
export { i18n };

// The choice made in this session. Local storage is the durable copy, but it is unwritable
// in a sandboxed iframe, and the loader has to be able to read back what the switcher set.
let selectedLocale: Locale | null = null;

/**
 * The locale to render in: the choice made in this session, a previously saved one from local
 * storage otherwise, and `sourceLocale` (Dutch) when there is neither.
 */
export function detectLocale(): Locale {
   if (selectedLocale) return selectedLocale;

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
   selectedLocale = locale;

   try {
      localStorage.setItem(LOCALE_STORAGE_KEY, locale);
   } catch {
      // Sandboxed iframe: the choice simply does not survive a reload.
   }
}

/**
 * Root route loader: activates the catalogue of the chosen locale. Loading it here rather
 * than in the language switcher is what makes a switch a piece of router work, so it runs
 * behind the navigation progress bar like every other load.
 */
export async function localeLoader(): Promise<null> {
   const locale = detectLocale();
   if (i18n.locale !== locale) {
      await loadCatalog(locale);
   }
   return null;
}
