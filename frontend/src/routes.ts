import { index, type RouteConfig, type RouteConfigEntry, route } from "@react-router/dev/routes";

// Route ids must be unique, so each mount of these pages gets its own suffix.
function municipalityRoutes(idSuffix: string): RouteConfigEntry[] {
   return [
      index("pages/MunicipalityPage/MunicipalityPollingstationListPage.tsx", {
         id: `MunicipalityPollingstationListPage${idSuffix}`,
      }),
      route("resultaten", "pages/MunicipalityPage/MunicipalityResultsPage.tsx", {
         id: `MunicipalityResultsPage${idSuffix}`,
      }),
      route("resultaten/:partySlug", "pages/MunicipalityPage/MunicipalityPartyResultsPage.tsx", {
         id: `MunicipalityPartyResultsPage${idSuffix}`,
      }),
      route(":pollingStationSlug", "pages/PollingStationPage/PollingStationResultsPage.tsx", {
         id: `PollingStationResultsPage${idSuffix}`,
      }),
      route(":pollingStationSlug/:partySlug", "pages/PollingStationPage/PollingStationPartyResultsPage.tsx", {
         id: `PollingStationPartyResultsPage${idSuffix}`,
      }),
   ];
}

// Routes are only nested where the parent path ends in a route parameter: that is where
// a loader for that parameter belongs. Static segments (csb, gsb, resultaten) stay
// inline in the child path rather than adding an empty level. The parameter levels have no
// page of their own, so they render a bare `Outlet`.
export default [
   index("pages/HomePage.tsx", { id: "HomePage" }),
   route(":electionConfigSlug", "components/RouteOutlet.tsx", { id: "ElectionConfigRoute" }, [
      index("pages/NotFoundPage.tsx", { id: "NotFoundPage" }),
      route("fout-melden", "pages/ReportIssuePage.tsx", { id: "ReportIssuePage" }),
      route("van-stem-tot-uitslag", "pages/ElectionConfigPage/ElectionConfigTimelinePage.tsx", {
         id: "ElectionConfigTimelinePage",
      }),
      route("csb", "pages/ElectionConfigPage/ElectionConfigCSBListPage.tsx", { id: "ElectionConfigCSBListPage" }),
      route("csb/:regionSlug", "components/RouteOutlet.tsx", { id: "CSBRegionRoute" }, [
         index("pages/CSBPage/CSBMunicipalityListPage.tsx", { id: "CSBMunicipalityListPage" }),
         route("resultaten", "pages/CSBPage/CSBResultsPage.tsx", { id: "CSBResultsPage" }),
         route("resultaten/:partySlug", "pages/CSBPage/CSBPartyResultsPage.tsx", { id: "CSBPartyResultsPage" }),
      ]),
      route("hsb", "pages/ElectionConfigPage/ElectionConfigHSBListPage.tsx", { id: "ElectionConfigHSBListPage" }),
      route("hsb/:regionSlug", "components/RouteOutlet.tsx", { id: "HSBRegionRoute" }, [
         index("pages/HSBPage/HSBMunicipalityListPage.tsx", { id: "HSBMunicipalityListPage" }),
         route("resultaten", "pages/HSBPage/HSBResultsPage.tsx", { id: "HSBResultsPage" }),
         route("resultaten/:partySlug", "pages/HSBPage/HSBPartyResultsPage.tsx", { id: "HSBPartyResultsPage" }),
      ]),
      route("gsb", "pages/ElectionConfigPage/ElectionConfigMunicipalityListPage.tsx", {
         id: "ElectionConfigMunicipalityListPage",
      }),
      route(
         "gsb/:regionSlug/csb/:csbSlug",
         "components/RouteOutlet.tsx",
         { id: "MunicipalityRoute" },
         municipalityRoutes(""),
      ),
      // A GR gemeente is its own CSB, so there is no CSB above it to name.
      route(
         "gsb/:regionSlug",
         "components/RouteOutlet.tsx",
         { id: "MunicipalityRouteWithoutCsb" },
         municipalityRoutes("WithoutCsb"),
      ),
      route("*", "pages/NotFoundPage.tsx", { id: "NotFoundPageNested" }),
   ]),
   route("*", "pages/NotFoundPage.tsx", { id: "NotFoundPageRoot" }),
] satisfies RouteConfig;
