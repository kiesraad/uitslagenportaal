import { createBrowserRouter, Outlet, type RouteObject, ScrollRestoration } from "react-router";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage.tsx";
import LoadingPage from "@/pages/LoadingPage.tsx";
import MunicipalityPageLayout from "@/pages/MunicipalityPage/MunicipalityPageLayout.tsx";
import { CSBMunicipalityListPage } from "./pages/CSBPage/CSBMunicipalityListPage.tsx";
import { CSBPartyResultsPage } from "./pages/CSBPage/CSBPartyResultsPage.tsx";
import { CSBResultsPage } from "./pages/CSBPage/CSBResultsPage.tsx";
import { ElectionConfigCSBListPage, electionConfigLoader } from "./pages/ElectionConfigPage/ElectionConfigCSBListPage";
import { ElectionConfigMunicipalityListPage } from "./pages/ElectionConfigPage/ElectionConfigMunicipalityListPage";
import { HomePage } from "./pages/HomePage";
import { MunicipalityPartyResultsPage } from "./pages/MunicipalityPage/MunicipalityPartyResultsPage";
import { MunicipalityPollingstationListPage } from "./pages/MunicipalityPage/MunicipalityPollingstationListPage";
import { MunicipalityResultsPage } from "./pages/MunicipalityPage/MunicipalityResultsPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import PollingStationPartyResultsPage from "./pages/PollingStationPage/PollingStationPartyResultsPage.tsx";
import PollingStationResultsPage from "./pages/PollingStationPage/PollingStationResultsPage.tsx";
import { ReportIssuePage } from "./pages/ReportIssuePage";
import { queryClient } from "./queryClient.ts";

// Data mode has no slot outside the route tree, so the app-wide scroll behaviour hangs
// off a root layout route.
function RootLayout() {
   return (
      <>
         <ScrollRestoration />
         <Outlet />
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
            loader: electionConfigLoader(queryClient),
            ErrorBoundary: ErrorBoundaryPage,
            children: [
               { index: true, Component: NotFoundPage },
               { path: "fout-melden", Component: ReportIssuePage },
               { path: "csb", Component: ElectionConfigCSBListPage },
               {
                  path: "csb/:regionSlug",
                  children: [
                     { index: true, Component: CSBMunicipalityListPage },
                     { path: "resultaten", Component: CSBResultsPage },
                     { path: "resultaten/:partySlug", Component: CSBPartyResultsPage },
                  ],
               },
               { path: "gsb", Component: ElectionConfigMunicipalityListPage },
               {
                  path: "gsb/:regionSlug/csb/:csbSlug",
                  children: [
                     {
                        Component: MunicipalityPageLayout,
                        children: [
                           { index: true, Component: MunicipalityPollingstationListPage },
                           { path: "resultaten", Component: MunicipalityResultsPage },
                        ],
                     },
                     { path: "resultaten/:partySlug", Component: MunicipalityPartyResultsPage },
                     {
                        path: ":pollingStationSlug",
                        children: [
                           { index: true, Component: PollingStationResultsPage },
                           { path: ":partySlug", Component: PollingStationPartyResultsPage },
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
