import { Suspense } from "react";
import { createBrowserRouter, type LazyRouteFunction, Outlet, type RouteObject, ScrollRestoration } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import { LocaleProvider } from "@/components/LocaleProvider.tsx";
import { RouteFocus } from "@/components/RouteFocus.tsx";
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

function lazyPage<TModule>(
   importer: () => Promise<TModule>,
   select: (module: TModule) => Awaited<ReturnType<LazyRouteFunction<RouteObject>>>,
): LazyRouteFunction<RouteObject> {
   return async () => select(await importer());
}

// Route ids must be unique, so each mount of these pages gets its own suffix.
function municipalityRoutes(idSuffix: string): RouteObject[] {
   return [
      {
         index: true,
         id: `MunicipalityPollingstationListPage${idSuffix}`,
         lazy: lazyPage(
            () => import("./pages/MunicipalityPage/MunicipalityPollingstationListPage"),
            (m) => ({
               Component: m.MunicipalityPollingstationListPage,
               loader: m.municipalityPollingstationListLoader(queryClient),
            }),
         ),
      },
      {
         path: "resultaten",
         id: `MunicipalityResultsPage${idSuffix}`,
         lazy: lazyPage(
            () => import("./pages/MunicipalityPage/MunicipalityResultsPage"),
            (m) => ({
               Component: m.MunicipalityResultsPage,
               loader: m.municipalityResultsLoader(queryClient),
            }),
         ),
      },
      {
         path: "resultaten/:partySlug",
         id: `MunicipalityPartyResultsPage${idSuffix}`,
         lazy: async () => {
            const [page, results] = await Promise.all([
               import("./pages/MunicipalityPage/MunicipalityPartyResultsPage"),
               import("./pages/MunicipalityPage/MunicipalityResultsPage"),
            ]);
            return {
               Component: page.MunicipalityPartyResultsPage,
               loader: results.municipalityResultsLoader(queryClient),
            };
         },
      },
      {
         path: ":pollingStationSlug",
         id: `PollingStationResultsPage${idSuffix}`,
         lazy: lazyPage(
            () => import("./pages/PollingStationPage/PollingStationResultsPage.tsx"),
            (m) => ({
               Component: m.default,
               loader: m.pollingStationLoader(queryClient),
            }),
         ),
      },
      {
         path: ":pollingStationSlug/:partySlug",
         id: `PollingStationPartyResultsPage${idSuffix}`,
         lazy: async () => {
            const [page, results] = await Promise.all([
               import("./pages/PollingStationPage/PollingStationPartyResultsPage.tsx"),
               import("./pages/PollingStationPage/PollingStationResultsPage.tsx"),
            ]);
            return {
               Component: page.default,
               loader: results.pollingStationLoader(queryClient),
            };
         },
      },
   ];
}

// Routes are only nested where the parent path ends in a route parameter: that is where
// a loader for that parameter belongs. Static segments (csb, gsb, resultaten) stay
// inline in the child path rather than adding an empty level.
export const routes: RouteObject[] = [
   {
      id: "root",
      path: "/",
      loader: localeLoader,
      Component: RootLayout,
      ErrorBoundary: RootErrorBoundary,
      HydrateFallback: RootHydrateFallback,
      children: [
         {
            index: true,
            id: "HomePage",
            lazy: lazyPage(
               () => import("./pages/HomePage"),
               (m) => ({ Component: m.HomePage }),
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
                     () => Promise.all([import("./pages/ReportIssuePage"), import("./pages/ReportIssuePage.loader")]),
                     ([page, loader]) => ({
                        Component: page.ReportIssuePage,
                        loader: loader.reportIssueLoader(queryClient),
                     }),
                  ),
               },
               {
                  path: "van-stem-tot-uitslag",
                  id: "ElectionConfigTimelinePage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigTimelinePage"),
                     (m) => ({
                        Component: m.ElectionConfigTimelinePage,
                        loader: m.electionConfigTimelineLoader(queryClient),
                     }),
                  ),
               },
               {
                  path: "csb",
                  id: "ElectionConfigCSBListPage",
                  lazy: lazyPage(
                     () => import("./pages/ElectionConfigPage/ElectionConfigCSBListPage"),
                     (m) => ({
                        Component: m.ElectionConfigCSBListPage,
                        loader: m.electionConfigCSBListLoader(queryClient),
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
                              Component: m.CSBMunicipalityListPage,
                              loader: m.csbMunicipalityListLoader(queryClient),
                           }),
                        ),
                     },
                     {
                        path: "resultaten",
                        id: "CSBResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/CSBPage/CSBResultsPage.tsx"),
                           (m) => ({
                              Component: m.CSBResultsPage,
                              loader: m.csbResultsLoader(queryClient),
                           }),
                        ),
                     },
                     {
                        path: "resultaten/:partySlug",
                        id: "CSBPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/CSBPage/CSBPartyResultsPage.tsx"),
                           (m) => ({
                              Component: m.CSBPartyResultsPage,
                              loader: m.csbPartyResultsLoader(queryClient),
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
                        Component: m.ElectionConfigHSBListPage,
                        loader: m.electionConfigHSBListLoader(queryClient),
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
                              Component: m.HSBMunicipalityListPage,
                              loader: m.hsbMunicipalityListLoader(queryClient),
                           }),
                        ),
                     },
                     {
                        path: "resultaten",
                        id: "HSBResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/HSBPage/HSBResultsPage.tsx"),
                           (m) => ({
                              Component: m.HSBResultsPage,
                              loader: m.hsbResultsLoader(queryClient),
                           }),
                        ),
                     },
                     {
                        path: "resultaten/:partySlug",
                        id: "HSBPartyResultsPage",
                        lazy: lazyPage(
                           () => import("./pages/HSBPage/HSBPartyResultsPage.tsx"),
                           (m) => ({
                              Component: m.HSBPartyResultsPage,
                              loader: m.hsbPartyResultsLoader(queryClient),
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
                        Component: m.ElectionConfigMunicipalityListPage,
                        loader: m.electionConfigMunicipalityListLoader(queryClient),
                     }),
                  ),
               },
               {
                  path: "gsb/:regionSlug/csb/:csbSlug",
                  children: municipalityRoutes(""),
               },
               {
                  // A GR gemeente is its own CSB, so there is no CSB above it to name.
                  path: "gsb/:regionSlug",
                  children: municipalityRoutes("WithoutCsb"),
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
