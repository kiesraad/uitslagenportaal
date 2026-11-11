import { I18nProvider } from "@lingui/react";
import type { ReactNode } from "react";
import { useRouteLoaderData } from "react-router";
import { detectLocale, getLoadedI18n } from "@/i18n";
import type { loadRoot } from "@/router.tsx";

/**
 * Provides the i18n instance of the locale the root loader loaded, so a language switch swaps the
 * instance. Before that loader has run, and in its error boundary, the detected locale is used, or
 * an already loaded one when the detected locale's catalogue failed to load.
 */
export function LocaleProvider({ children }: { children: ReactNode }) {
   const rootData = useRouteLoaderData<typeof loadRoot>("root");
   const locale = rootData?.locale ?? detectLocale();

   return <I18nProvider i18n={getLoadedI18n(locale)}>{children}</I18nProvider>;
}
