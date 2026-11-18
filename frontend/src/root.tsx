import { config as fontAwesomeConfig } from "@fortawesome/fontawesome-svg-core";
import "@fortawesome/fontawesome-svg-core/styles.css";
import { dehydrate, HydrationBoundary, type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode, Suspense, useState } from "react";
import { Links, Meta, Outlet, Scripts, ScrollRestoration, useMatches } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LocaleProvider, useRootI18n } from "@/components/LocaleProvider.tsx";
import { RouteFocus } from "@/components/RouteFocus.tsx";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import "./index.css";
import { electionConfigsQuery } from "./hooks/queries.ts";
import { loadCatalog, localeFromCookieHeader, localeLoader } from "./i18n";
import { createQueryClient, createServerQueryClient, queryClient, type ServerLoaderData } from "./queryClient.ts";
import type { Route } from "./+types/root";

// The icon styles ship with the page's CSS; injected at runtime, prerendered icons show unstyled until then.
fontAwesomeConfig.autoAddCss = false;

/** Loads the locale; the Footer's election list is prefetched without awaiting it or surfacing its failure. */
export function loadRoot(client: QueryClient) {
   client.query(electionConfigsQuery()).catch(() => {});
   return localeLoader();
}

// Renders the page in the language the visitor chose before, saved in the `lang` cookie. The election
// list fills the Footer and tabs; without it they render without the list, as in the browser.
export async function loader({ request }: Route.LoaderArgs) {
   const client = createServerQueryClient();
   const [locale] = await Promise.all([
      loadCatalog(localeFromCookieHeader(request.headers.get("Cookie"))),
      client.query(electionConfigsQuery()).catch(() => {}),
   ]);
   return { locale, dehydratedState: dehydrate(client) };
}

export const clientLoader = () => loadRoot(queryClient);

/** The query data the server loaders of all matched routes rendered the page with. */
function useServerQueries(): ServerLoaderData["dehydratedState"] {
   const queries = useMatches().flatMap(
      (match) => (match.loaderData as Partial<ServerLoaderData> | undefined)?.dehydratedState?.queries ?? [],
   );
   return { mutations: [], queries };
}

// Wraps the routes and the error boundaries alike, so every one of them has the providers.
// React Router renders Layout separately around App, ErrorBoundary and HydrateFallback, so it remounts on a swap.
export function Layout({ children }: { children: ReactNode }) {
   const { locale } = useRootI18n();
   // A server shares this module between requests, so each render gets a query cache of its own.
   const [client] = useState(() => (import.meta.env.SSR ? createQueryClient() : queryClient));
   const serverQueries = useServerQueries();

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
            <QueryClientProvider client={client}>
               <HydrationBoundary state={serverQueries}>
                  <LocaleProvider>{children}</LocaleProvider>
               </HydrationBoundary>
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
