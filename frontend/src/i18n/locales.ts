/**
 * Locale facts, kept free of React and Lingui imports so that config, tests and
 * components can all share one definition.
 */

export const locales = ["nl", "en"] as const;

export type Locale = (typeof locales)[number];

/** Source language of the messages written in the source files. */
export const sourceLocale: Locale = "nl";

export const LOCALE_STORAGE_KEY = "lang";

function isLocale(candidate: string): candidate is Locale {
   return (locales as readonly string[]).includes(candidate);
}

/**
 * Narrows an arbitrary language tag to a supported locale, falling back to the
 * source locale. Regional tags resolve to their base language, so `en-GB` and
 * `en-US` both become `en`.
 *
 * `null` and `undefined` are accepted because both `detect()` and
 * `localStorage.getItem()` can return them.
 */
export function resolveLocale(candidate: string | null | undefined): Locale {
   if (!candidate) return sourceLocale;
   if (isLocale(candidate)) return candidate;

   const base = candidate.split("-")[0];
   return isLocale(base) ? base : sourceLocale;
}

/**
 * The name of a language written in that language itself — "Nederlands" rather
 * than "Dutch" — which is what a language switcher should offer.
 */
export function localeDisplayName(locale: Locale): string {
   return new Intl.DisplayNames([locale], { type: "language" }).of(locale) ?? locale;
}
