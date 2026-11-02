import { type I18n, type Messages, setupI18n } from "@lingui/core";
import { readCookie, writeCookie } from "@/utils/cookies.ts";
import { LOCALE_COOKIE, type Locale, resolveLocale, sourceLocale } from "./locales";

export * from "./locales";

// Catalogues never change once loaded, so a server can share one instance per locale between requests.
const instances = new Map<Locale, I18n>();

/** The i18n instance for a locale; its catalogue is active once `loadCatalog` has resolved for it. */
export function getI18n(locale: Locale): I18n {
   let instance = instances.get(locale);
   if (!instance) {
      instance = setupI18n();
      instances.set(locale, instance);
   }
   return instance;
}

// The choice made in this session, which also outlives a cookie the browser refuses to store
let selectedLocale: Locale | null = null;

/**
 * The locale to render in: the choice made in this session, a previously saved one from the `lang`
 * cookie otherwise, and `sourceLocale` (Dutch) when there is neither.
 */
export function detectLocale(): Locale {
   return selectedLocale ?? resolveLocale(readCookie(LOCALE_COOKIE));
}

/**
 * Loads a catalogue, falling back to `sourceLocale` when it fails. The import specifier must
 * stay a template literal: that is what lets Vite emit one lazily loaded chunk per locale, so a
 * visitor only downloads the language they are actually reading.
 */
async function loadMessages(locale: Locale): Promise<{ locale: Locale; messages: Messages }> {
   try {
      const { messages } = await import(`../locales/${locale}/messages.po`);
      return { locale, messages };
   } catch (error) {
      console.error(`Catalog for "${locale}" failed to load, falling back to "${sourceLocale}"`, error);
      const { messages } = await import(`../locales/${sourceLocale}/messages.po`);
      return { locale: sourceLocale, messages };
   }
}

/** Loads a locale's catalogue into its instance, once. Returns the locale that ended up loaded. */
export async function loadCatalog(locale: Locale): Promise<Locale> {
   if (getI18n(locale).locale === locale) return locale;

   const catalog = await loadMessages(locale);
   getI18n(catalog.locale).loadAndActivate(catalog);
   return catalog.locale;
}

/** Remembers the chosen locale in a cookie, which a server render can read too. */
export function saveLocale(locale: Locale): void {
   selectedLocale = locale;
   writeCookie(LOCALE_COOKIE, locale);
}

/** The locale named by the `lang` cookie in a raw `Cookie` header, for rendering on a server. */
export function localeFromCookieHeader(cookieHeader: string | null | undefined): Locale {
   return resolveLocale(readCookie(LOCALE_COOKIE, cookieHeader ?? ""));
}

/**
 * Root route loader: loads the catalogue of the chosen locale. Loading it here rather than in the
 * language switcher is what makes a switch a piece of router work, so it runs behind the navigation
 * progress bar like every other load. The root route renders its I18nProvider from the result.
 */
export async function localeLoader(): Promise<{ locale: Locale }> {
   const locale = await loadCatalog(detectLocale());
   document.documentElement.lang = locale;
   return { locale };
}
