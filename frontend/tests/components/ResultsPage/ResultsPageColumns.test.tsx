import { QueryClient } from "@tanstack/react-query";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ElectionConfig } from "@/api/types";
import ResultsPageColumns from "@/components/ResultsPage/ResultsPageColumns";
import { electionConfigQuery } from "@/hooks/queries";
import { renderWithProviders } from "../../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00+01:00",
   csb_type: "WATERSCHAP",
   has_hsb: false,
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

describe("ResultsPageColumns", () => {
   it("Shows the proces-verbaal stub on the Vite dev server", () => {
      const queryClient = new QueryClient({
         defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
      });
      const query = electionConfigQuery(electionConfig.slug);
      queryClient.setQueryData(query.queryKey, electionConfig);

      renderWithProviders(
         <ResultsPageColumns>
            <p>Results</p>
         </ResultsPageColumns>,
         {
            initialEntries: [`/${electionConfig.slug}/gsb/lisserdam`],
            path: "/:electionConfigSlug/*",
            queryClient,
         },
      );

      expect(screen.getByText("Results")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });
});
