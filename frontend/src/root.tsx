import { config as fontAwesomeConfig } from "@fortawesome/fontawesome-svg-core";
import "@fortawesome/fontawesome-svg-core/styles.css";
import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, Suspense } from "react";
import { Links, Meta, Outlet, Scripts, ScrollRestoration } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LocaleProvider, useRootI18n } from "@/components/LocaleProvider.tsx";
import { RouteFocus } from "@/components/RouteFocus.tsx";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import "./index.css";
import { electionConfigsQuery } from "./hooks/queries.ts";
import { loadCatalog, localeLoader, sourceLocale } from "./i18n";
import { queryClient } from "./queryClient.ts";

// The icon styles ship with the page's CSS; injected at runtime, prerendered icons show unstyled until then.
fontAwesomeConfig.autoAddCss = false;

/** Loads the locale; the Footer's election list is prefetched without awaiting it or surfacing its failure. */
export function loadRoot(client: QueryClient) {
   client.query(electionConfigsQuery()).catch(() => {});
   return localeLoader();
}

// Runs only to prerender the shell (at build time, and per request under `react-router dev`),
// loading the catalogue that shell is rendered in.
export async function loader() {
   return { locale: await loadCatalog(sourceLocale) };
}

export const clientLoader = () => loadRoot(queryClient);
// Also runs on the first visit, to load the visitor's locale rather than keep the shell's.
clientLoader.hydrate = true as const;

// Wraps the routes and the error boundaries alike, so every one of them has the providers.
// React Router renders Layout separately around App, ErrorBoundary and HydrateFallback, so it remounts on a swap.
export function Layout({ children }: { children: ReactNode }) {
   const { locale } = useRootI18n();

   return (
      <html lang={locale}>
         <head>
            <meta charSet="UTF-8" />
            <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <meta name="robots" content="index, follow" />
            <meta property="og:type" content="website" />
            <meta property="og:site_name" content="Uitslagenportaal - Kiesraad" />
            <Meta />
            <Links />
         </head>
         <body className="flex min-h-dvh flex-col text-gray-900">
            <RouteFocus />
            <QueryClientProvider client={queryClient}>
               <LocaleProvider>{children}</LocaleProvider>
            </QueryClientProvider>
            <ScrollRestoration />
            <Scripts />
         </body>
      </html>
   );
}

// The Suspense boundary catches the suspense queries the pages read: their loaders normally warm
// the cache first, so it only shows if an entry was evicted by the garbage collector while the
// page stayed mounted.
export default function App() {
   return (
      <Suspense fallback={<LoadingPage />}>
         <BaseLayout>
            <Outlet />
         </BaseLayout>
      </Suspense>
   );
}

export const ErrorBoundary = ErrorBoundaryPage;

export const HydrateFallback = LoadingPage;
