import { QueryClient } from "@tanstack/react-query";
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ElectionConfig, Region } from "@/api/types";
import { electionConfigQuery, regionQuery } from "@/hooks/queries";
import PollingStationPartyResultsPage from "@/pages/PollingStationPage/PollingStationPartyResultsPage";
import PollingStationResultsPage from "@/pages/PollingStationPage/PollingStationResultsPage";
import { renderWithProviders } from "../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00",
   csb_type: "WATERSCHAP",
   single_csb: null,
   has_hsb: false,
   timeline_dates: [],
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

const gemeente: Region = {
   region_name: "Borsele",
   slug: "654-borsele",
   vote_counts: [],
   region_category: "GEMEENTE",
   results_available_at: null,
   has_hsb: false,
   is_csb: false,
   hsb: null,
   csb: {
      id: 17,
      election_id: 1,
      parent_id: 1,
      region_number: "17",
      region_category: "WATERSCHAP",
      region_name: "Scheldestromen",
      slug: "17-scheldestromen",
   },
};

const pollingStation: Region = {
   region_name: "De Regenboog",
   slug: "SB1-de-regenboog",
   vote_counts: [],
   region_category: "STEMBUREAU",
   results_available_at: null,
   has_hsb: false,
   is_csb: false,
   hsb: null,
   station_number: 1,
   csb: gemeente.csb,
};

function seedPollingStationQueries() {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   const electionQuery = electionConfigQuery(electionConfig.slug);
   const gemeenteQuery = regionQuery(
      {
         electionConfigSlug: electionConfig.slug,
         regionSlug: gemeente.slug,
         csbSlug: gemeente.csb?.slug,
      },
      "gsb",
   );
   const stationQuery = regionQuery(
      {
         electionConfigSlug: electionConfig.slug,
         regionSlug: pollingStation.slug,
         csbSlug: gemeente.csb?.slug,
         parentRegionSlug: gemeente.slug,
      },
      "sb",
   );
   queryClient.setQueryData(electionQuery.queryKey, electionConfig);
   queryClient.setQueryData(gemeenteQuery.queryKey, gemeente);
   queryClient.setQueryData(stationQuery.queryKey, pollingStation);
   return {
      queryClient,
      loaderData: {
         electionConfigQuery: electionQuery,
         regionQuery: gemeenteQuery,
         pollingStationQuery: stationQuery,
      },
   };
}

describe("PollingStationPages", () => {
   it("puts the padded station number on the stembureau breadcrumb, not the heading", () => {
      const { queryClient, loaderData } = seedPollingStationQueries();
      renderWithProviders(<PollingStationResultsPage />, {
         path: "/:electionConfigSlug/gsb/:regionSlug/csb/:csbSlug/:pollingStationSlug",
         initialEntries: [
            `/${electionConfig.slug}/gsb/${gemeente.slug}/csb/${gemeente.csb?.slug}/${pollingStation.slug}`,
         ],
         loaderData,
         queryClient,
      });

      const crumbs = screen.getByRole("navigation", { name: "Kruimelpad" });
      expect(within(crumbs).getByText("001 - De Regenboog")).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("De Regenboog");
      expect(screen.getByRole("heading", { level: 1 })).not.toHaveTextContent("001");
   });

   it("keeps the padded station number on the party-results breadcrumb", () => {
      const { queryClient, loaderData } = seedPollingStationQueries();
      renderWithProviders(<PollingStationPartyResultsPage />, {
         path: "/:electionConfigSlug/gsb/:regionSlug/csb/:csbSlug/:pollingStationSlug/:partySlug",
         initialEntries: [
            `/${electionConfig.slug}/gsb/${gemeente.slug}/csb/${gemeente.csb?.slug}/${pollingStation.slug}/vvd`,
         ],
         loaderData,
         queryClient,
      });

      const crumbs = screen.getByRole("navigation", { name: "Kruimelpad" });
      expect(within(crumbs).getByRole("link", { name: "001 - De Regenboog" })).toBeInTheDocument();
   });
});
