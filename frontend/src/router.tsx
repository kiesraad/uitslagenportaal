import { Suspense } from "react";
import { createBrowserRouter, Outlet, type RouteObject, ScrollRestoration } from "react-router";
import { BaseLayout } from "@/components/BaseLayout.tsx";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import MunicipalityPageLayout, { municipalityLoader } from "@/pages/MunicipalityPage/MunicipalityPageLayout.tsx";
import { CSBMunicipalityListPage, csbMunicipalityListLoader } from "./pages/CSBPage/CSBMunicipalityListPage.tsx";
import { CSBPartyResultsPage, csbPartyResultsLoader } from "./pages/CSBPage/CSBPartyResultsPage.tsx";
import { CSBResultsPage, csbResultsLoader } from "./pages/CSBPage/CSBResultsPage.tsx";
import {
   ElectionConfigCSBListPage,
   electionConfigCSBListLoader,
} from "./pages/ElectionConfigPage/ElectionConfigCSBListPage";
import {
   ElectionConfigMunicipalityListPage,
   electionConfigMunicipalityListLoader,
} from "./pages/ElectionConfigPage/ElectionConfigMunicipalityListPage";
import { HomePage } from "./pages/HomePage";
import { MunicipalityPartyResultsPage } from "./pages/MunicipalityPage/MunicipalityPartyResultsPage";
import {
   MunicipalityPollingstationListPage,
   municipalityPollingstationListLoader,
} from "./pages/MunicipalityPage/MunicipalityPollingstationListPage";
import { MunicipalityResultsPage } from "./pages/MunicipalityPage/MunicipalityResultsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import PollingStationPartyResultsPage from "./pages/PollingStationPage/PollingStationPartyResultsPage.tsx";
import PollingStationResultsPage, {
   pollingStationLoader,
} from "./pages/PollingStationPage/PollingStationResultsPage.tsx";
import { ReportIssuePage, reportIssueLoader } from "./pages/ReportIssuePage";
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

// Routes are only nested where the parent path ends in a route parameter: that is where
// a loader for that parameter belongs. Static segments (csb, gsb, resultaten) stay
// inline in the child path rather than adding an empty level.
export const routes: RouteObject[] = [
   {
      path: "/",
      Component: RootLayout,
      ErrorBoundary: ErrorBoundaryPage,
      HydrateFallback: LoadingPage,
      children: [
         { index: true, Component: HomePage },
         {
            path: ":electionConfigSlug",
            children: [
               { index: true, Component: NotFoundPage },
               { path: "fout-melden", loader: reportIssueLoader(queryClient), Component: ReportIssuePage },
               { path: "csb", loader: electionConfigCSBListLoader(queryClient), Component: ElectionConfigCSBListPage },
               {
                  path: "csb/:regionSlug",
                  children: [
                     {
                        index: true,
                        loader: csbMunicipalityListLoader(queryClient),
                        Component: CSBMunicipalityListPage,
                     },
                     { path: "resultaten", loader: csbResultsLoader(queryClient), Component: CSBResultsPage },
                     {
                        path: "resultaten/:partySlug",
                        loader: csbPartyResultsLoader(queryClient),
                        Component: CSBPartyResultsPage,
                     },
                  ],
               },
               {
                  path: "gsb",
                  loader: electionConfigMunicipalityListLoader(queryClient),
                  Component: ElectionConfigMunicipalityListPage,
               },
               {
                  path: "gsb/:regionSlug/csb/:csbSlug",
                  children: [
                     {
                        // The layout loads the gemeente its two children render.
                        loader: municipalityLoader(queryClient),
                        Component: MunicipalityPageLayout,
                        children: [
                           {
                              index: true,
                              loader: municipalityPollingstationListLoader(queryClient),
                              Component: MunicipalityPollingstationListPage,
                           },
                           { path: "resultaten", Component: MunicipalityResultsPage },
                        ],
                     },
                     {
                        path: "resultaten/:partySlug",
                        loader: municipalityLoader(queryClient),
                        Component: MunicipalityPartyResultsPage,
                     },
                     {
                        path: ":pollingStationSlug",
                        children: [
                           {
                              index: true,
                              loader: pollingStationLoader(queryClient),
                              Component: PollingStationResultsPage,
                           },
                           {
                              path: ":partySlug",
                              loader: pollingStationLoader(queryClient),
                              Component: PollingStationPartyResultsPage,
                           },
                        ],
                     },
                  ],
               },
               { path: "*", Component: NotFoundPage },
            ],
         },
         { path: "*", Component: NotFoundPage },
      ],
   },
];

export const router = createBrowserRouter(routes);
