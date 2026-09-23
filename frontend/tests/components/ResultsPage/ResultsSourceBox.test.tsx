import { QueryClient } from "@tanstack/react-query";
import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ElectionConfig } from "@/api/types";
import ResultsSourceBox from "@/components/ResultsPage/ResultsSourceBox";
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

function renderBox(locale: "nl" | "en" = "nl", previewUrl?: string | null) {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   const query = electionConfigQuery(electionConfig.slug);
   queryClient.setQueryData(query.queryKey, electionConfig);

   return renderWithProviders(<ResultsSourceBox previewUrl={previewUrl} />, {
      locale,
      initialEntries: [`/${electionConfig.slug}/gsb/lisserdam`],
      path: "/:electionConfigSlug/*",
      queryClient,
   });
}

describe("ResultsSourceBox", () => {
   it("Shows the stub proces-verbaal preview and view link", () => {
      renderBox();

      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
      expect(screen.getByRole("img", { name: "Voorbeeld van een proces-verbaal" })).toHaveAttribute(
         "src",
         "/images/stub_pv_sb.png",
      );
      expect(screen.getByRole("link", { name: /Bekijk het proces-verbaal/ })).toHaveAttribute(
         "href",
         "/images/stub_pv_sb.png",
      );
      expect(screen.getByRole("link", { name: /Meld een fout of iets dat niet klopt/ })).toHaveAttribute(
         "href",
         "/ws2023/fout-melden",
      );
      expect(screen.getByText(/14 december om 10:00/)).toBeInTheDocument();
   });

   it("Shows the imported proces-verbaal preview when the region has one", () => {
      const previewUrl = "/api/certified-documents/7/preview/";
      renderBox("nl", previewUrl);

      expect(screen.getByRole("img", { name: "Voorbeeld van een proces-verbaal" })).toHaveAttribute("src", previewUrl);
      expect(screen.getByRole("link", { name: /Bekijk het proces-verbaal/ })).toHaveAttribute("href", previewUrl);
   });

   it("Renders the source box in English when that locale is active", () => {
      renderBox("en");

      expect(screen.getByRole("heading", { name: "Where do these counting results come from?" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /View the certified election results/ })).toBeInTheDocument();
      expect(screen.getByText(/14 December at 10:00/)).toBeInTheDocument();
   });
});
