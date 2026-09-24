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

function renderBox(locale: "nl" | "en" = "nl", previewUrl?: string | null, documentUrl?: string | null) {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   const query = electionConfigQuery(electionConfig.slug);
   queryClient.setQueryData(query.queryKey, electionConfig);

   return renderWithProviders(<ResultsSourceBox previewUrl={previewUrl} documentUrl={documentUrl} />, {
      locale,
      initialEntries: [`/${electionConfig.slug}/gsb/lisserdam`],
      path: "/:electionConfigSlug/*",
      queryClient,
   });
}

describe("ResultsSourceBox", () => {
   it("Says the proces-verbaal has not arrived yet when the region has none", () => {
      renderBox();

      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
      expect(screen.getByText("Het proces-verbaal is nog niet ontvangen")).toBeInTheDocument();
      expect(screen.getByText("Het verschijnt hier zodra het is binnengekomen.")).toBeInTheDocument();
      expect(screen.queryByRole("img", { name: "Proces-verbaal" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Bekijk het proces-verbaal/ })).not.toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Meld een fout of iets dat niet klopt/ })).toHaveAttribute(
         "href",
         "/ws2023/fout-melden",
      );
      expect(screen.getByText(/14 december om 10:00/)).toBeInTheDocument();
   });

   it("Opens the full proces-verbaal from the picture and from the link", () => {
      const previewUrl = "/api/certified-documents/7/preview/";
      const documentUrl = "/api/certified-documents/7/";
      renderBox("nl", previewUrl, documentUrl);

      expect(screen.getByRole("img", { name: "Proces-verbaal" })).toHaveAttribute("src", previewUrl);
      const links = screen.getAllByRole("link", { name: /proces-verbaal/i });
      expect(links).toHaveLength(2);
      for (const link of links) {
         expect(link).toHaveAttribute("href", documentUrl);
         expect(link).toHaveAttribute("target", "_blank");
      }
   });

   it("Renders the source box in English when that locale is active", () => {
      renderBox("en");

      expect(screen.getByRole("heading", { name: "Where do these counting results come from?" })).toBeInTheDocument();
      expect(screen.getByText("The certified election results have not arrived yet")).toBeInTheDocument();
      expect(screen.getByText("They will appear here once they have been received.")).toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /View the certified election results/ })).not.toBeInTheDocument();
      expect(screen.getByText(/14 December at 10:00/)).toBeInTheDocument();
   });
});
