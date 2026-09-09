import { Suspense } from "react";
import { createBrowserRouter, type LazyRouteFunction, Outlet, type RouteObject, ScrollRestoration } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import { localeLoader } from "./i18n";
import { queryClient } from "./queryClient.ts";

// The Suspense boundary catches the suspense queries the pages
// read: their loaders normally warm the cache first, so it only shows if an entry was
// evicted by the garbage collector while the page stayed mounted.
function RootLayout() {
   return (
      <>
         <ScrollRestoration />
         <Suspense fallback={<LoadingPage />}>
            <BaseLayout>
               <Outlet />
            </BaseLayout>
         </Suspense>
      </>
   );
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
      path: "/",
      loader: localeLoader,
      Component: RootLayout,
      ErrorBoundary: ErrorBoundaryPage,
      HydrateFallback: LoadingPage,
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
                     () => import("./pages/ReportIssuePage"),
                     (m) => ({
                        Component: m.ReportIssuePage,
                        loader: m.reportIssueLoader(queryClient),
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
                  children: [
                     {
                        index: true,
                        id: "MunicipalityPollingstationListPage",
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
                        id: "MunicipalityResultsPage",
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
                        id: "MunicipalityPartyResultsPage",
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
                        id: "PollingStationResultsPage",
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
                        id: "PollingStationPartyResultsPage",
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
