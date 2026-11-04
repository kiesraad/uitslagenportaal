import type { QueryClient } from "@tanstack/react-query";
import { Suspense } from "react";
import { createBrowserRouter, type LazyRouteFunction, Outlet, type RouteObject, ScrollRestoration } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LocaleProvider } from "@/components/LocaleProvider.tsx";
import { RouteFocus } from "@/components/RouteFocus.tsx";
import { electionConfigsQuery } from "@/hooks/queries.ts";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import { localeLoader } from "./i18n";
import { queryClient } from "./queryClient.ts";

// The Suspense boundary catches the suspense queries the pages
// read: their loaders normally warm the cache first, so it only shows if an entry was
// evicted by the garbage collector while the page stayed mounted.
function RootLayout() {
   return (
      <LocaleProvider>
         <ScrollRestoration />
         <RouteFocus />
         <Suspense fallback={<LoadingPage />}>
            <BaseLayout>
               <Outlet />
            </BaseLayout>
         </Suspense>
      </LocaleProvider>
   );
}

function RootErrorBoundary() {
   return (
      <LocaleProvider>
         <ErrorBoundaryPage />
      </LocaleProvider>
   );
}

function RootHydrateFallback() {
   return (
      <LocaleProvider>
         <LoadingPage />
      </LocaleProvider>
   );
}

/** Loads the locale; the Footer's election list is prefetched without holding up the page. */
export function loadRoot(client: QueryClient) {
   void client.query(electionConfigsQuery());
   return localeLoader();
}

function lazyPage<TModule>(
   importer: () => Promise<TModule>,
   select: (module: TModule) => Awaited<ReturnType<LazyRouteFunction<RouteObject>>>,
): LazyRouteFunction<RouteObject> {
   return async () => select(await importer());
}

// Routes are only nested where the parent path ends in a route parameter: that is where
// a loader for that parameter belongs. Static segments (csb, gsb, resultaten) stay
// inline in the child path rather than adding an empty level.
export const routes: RouteObject[] = [
   {
      id: "root",
      path: "/",
      loader: () => loadRoot(queryClient),
      Component: RootLayout,
      ErrorBoundary: RootErrorBoundary,
      HydrateFallback: RootHydrateFallback,
      children: [
         {
            index: true,
            id: "HomePage",
            lazy: lazyPage(
               () => import("./pages/HomePage"),
               (m) => ({ Component: m.default, loader: () => m.loadHome(queryClient) }),
            ),
         },
         {
            path: ":electionConfigSlug",
            children: [
               {
                  index: true,
                  id: "NotFoundPage",
                  lazy: lazyPage(
                     () => import("./pages/NotFoundPage"),
                     (m) => ({ Component: m.NotFoundPage }),
                  ),
               },
               {
                  path: "fout-melden",
                  id: "ReportIssuePage",
                  lazy: lazyPage(
                     () => import("./pages/ReportIssuePage"),
                     (m) => ({ Component: m.default, loader: (args) => m.loadReportIssue(queryClient, args) }),
                  ),
               },
               {
                  path: "van-stem-tot-uitslag",
                  id: "ElectionConfigTimelinePage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigTimelinePage"),
                     (m) => ({
                        Component: m.default,
                        loader: (args) => m.loadElectionConfigTimeline(queryClient, args),
                     }),
                  ),
               },
               {
                  path: "csb",
                  id: "ElectionConfigCSBListPage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigCSBListPage"),
                     (m) => ({
                        Component: m.default,
                        loader: (args) => m.loadElectionConfigCSBList(queryClient, args),
                     }),
                  ),
               },
               {
                  path: "csb/:regionSlug",
                  children: [
                     {
                        index: true,
                        id: "CSBMunicipalityListPage",
                        lazy: lazyPage(
                           () => import("./pages/CSBPage/CSBMunicipalityListPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadCSBMunicipalityList(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: "resultaten",
                        id: "CSBResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/CSBPage/CSBResultsPage.tsx"),
                           (m) => ({ Component: m.default, loader: (args) => m.loadCSBResults(queryClient, args) }),
                        ),
                     },
                     {
                        path: "resultaten/:partySlug",
                        id: "CSBPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/CSBPage/CSBPartyResultsPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadCSBPartyResults(queryClient, args),
                           }),
                        ),
                     },
                  ],
               },
               {
                  path: "hsb",
                  id: "ElectionConfigHSBListPage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigHSBListPage"),
                     (m) => ({
                        Component: m.default,
                        loader: (args) => m.loadElectionConfigHSBList(queryClient, args),
                     }),
                  ),
               },
               {
                  path: "hsb/:regionSlug",
                  children: [
                     {
                        index: true,
                        id: "HSBMunicipalityListPage",
                        lazy: lazyPage(
                           () => import("./pages/HSBPage/HSBMunicipalityListPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadHSBMunicipalityList(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: "resultaten",
                        id: "HSBResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/HSBPage/HSBResultsPage.tsx"),
                           (m) => ({ Component: m.default, loader: (args) => m.loadHSBResults(queryClient, args) }),
                        ),
                     },
                     {
                        path: "resultaten/:partySlug",
                        id: "HSBPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/HSBPage/HSBPartyResultsPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadHSBPartyResults(queryClient, args),
                           }),
                        ),
                     },
                  ],
               },
               {
                  path: "gsb",
                  id: "ElectionConfigMunicipalityListPage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigMunicipalityListPage"),
                     (m) => ({
                        Component: m.default,
                        loader: (args) => m.loadElectionConfigMunicipalityList(queryClient, args),
                     }),
                  ),
               },
               {
                  path: "gsb/:regionSlug/csb/:csbSlug",
                  children: [
                     {
                        index: true,
                        id: "MunicipalityPollingstationListPage",
                        lazy: lazyPage(
                           () => import("./pages/MunicipalityPage/MunicipalityPollingstationListPage"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadMunicipalityPollingstationList(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: "resultaten",
                        id: "MunicipalityResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/MunicipalityPage/MunicipalityResultsPage"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadMunicipalityResults(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: "resultaten/:partySlug",
                        id: "MunicipalityPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/MunicipalityPage/MunicipalityPartyResultsPage"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadMunicipalityPartyResults(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: ":pollingStationSlug",
                        id: "PollingStationResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/PollingStationPage/PollingStationResultsPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadPollingStationResults(queryClient, args),
                           }),
                        ),
                     },
                     {
                        path: ":pollingStationSlug/:partySlug",
                        id: "PollingStationPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/PollingStationPage/PollingStationPartyResultsPage.tsx"),
                           (m) => ({
                              Component: m.default,
                              loader: (args) => m.loadPollingStationPartyResults(queryClient, args),
                           }),
                        ),
                     },
                  ],
               },
               {
                  path: "*",
                  id: "NotFoundPageNested",
                  lazy: lazyPage(
                     () => import("./pages/NotFoundPage"),
                     (m) => ({ Component: m.NotFoundPage }),
                  ),
               },
            ],
         },
         {
            path: "*",
            id: "NotFoundPageRoot",
            lazy: lazyPage(
               () => import("./pages/NotFoundPage"),
               (m) => ({ Component: m.NotFoundPage }),
            ),
         },
      ],
   },
];

export const router = createBrowserRouter(routes);
