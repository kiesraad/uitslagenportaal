import { I18nProvider } from "@lingui/react";
import type { ReactNode } from "react";
import { useRouteLoaderData } from "react-router";
import { detectLocale, getI18n, type localeLoader } from "@/i18n";

/**
 * Provides the i18n instance of the locale the root loader loaded, so a language switch swaps the
 * instance. Before that loader has run, and in its error boundary, the detected locale is used.
 */
export function LocaleProvider({ children }: { children: ReactNode }) {
   const rootData = useRouteLoaderData<typeof localeLoader>("root");
   const locale = rootData?.locale ?? detectLocale();

   return <I18nProvider i18n={getI18n(locale)}>{children}</I18nProvider>;
}
