import { I18nProvider } from "@lingui/react";
import type { ReactNode } from "react";
import { useRouteLoaderData } from "react-router";
import { getLoadedI18n, resolveLocale, sourceLocale } from "@/i18n";
import type { loadRoot } from "@/root.tsx";

/** The locale the prerendered shell is in, which hydration has to match. */
function shellLocale() {
   return typeof document === "undefined" ? sourceLocale : resolveLocale(document.documentElement.lang);
}

/**
 * The i18n instance of the locale the root loader loaded, so a language switch swaps the instance.
 * Without root loader data (hydrating, or the root loader failed) it is the shell's locale, or any
 * loaded one when that catalogue is missing.
 */
export function useRootI18n() {
   const rootData = useRouteLoaderData<typeof loadRoot>("root");
   return getLoadedI18n(rootData?.locale ?? shellLocale());
}

export function LocaleProvider({ children }: { children: ReactNode }) {
   return <I18nProvider i18n={useRootI18n()}>{children}</I18nProvider>;
}
