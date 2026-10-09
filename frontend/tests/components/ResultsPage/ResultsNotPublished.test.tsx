import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RegionCategory } from "@/api/types";
import ResultsNotPublished from "@/components/ResultsPage/ResultsNotPublished";
import { renderWithProviders } from "../../testUtils";

function renderBox(regionName: string, regionCategory: RegionCategory, locale: "nl" | "en" = "nl") {
   return renderWithProviders(<ResultsNotPublished regionName={regionName} regionCategory={regionCategory} />, {
      locale,
   });
}

describe("ResultsNotPublished", () => {
   it("Names the municipality with its type and article", () => {
      renderBox("Blaricum", "GEMEENTE");

      expect(screen.getByRole("heading", { name: /de gemeente Blaricum/ })).toBeInTheDocument();
      expect(
         screen.getByText(
            "De telresultaten en processen-verbaal van de gemeente Blaricum zijn hier te zien zodra de gemeente Blaricum ze publiceert.",
         ),
      ).toBeInTheDocument();
   });

   it("Uses het for a waterschap and a polling station", () => {
      const { unmount } = renderBox("Delfland", "WATERSCHAP");
      expect(screen.getByRole("heading", { name: /het waterschap Delfland/ })).toBeInTheDocument();
      unmount();

      renderBox("De Regenboog", "STEMBUREAU");
      expect(screen.getByRole("heading", { name: /het stembureau De Regenboog/ })).toBeInTheDocument();
   });

   it("Uses Nederland and the Kiesraad for a STAAT CSB", () => {
      renderBox("Nederland", "STAAT");

      expect(
         screen.getByRole("heading", { name: "De telresultaten van Nederland zijn nog niet gepubliceerd" }),
      ).toBeInTheDocument();
      expect(
         screen.getByText(
            "De telresultaten en processen-verbaal van Nederland zijn hier te zien zodra de Kiesraad ze publiceert.",
         ),
      ).toBeInTheDocument();
   });

   it("Uses the Electoral Council in English for a STAAT CSB", () => {
      renderBox("Nederland", "STAAT", "en");

      expect(screen.queryByText(/Nederland/)).not.toBeInTheDocument();
      expect(
         screen.getByText(
            "The counting results and certified election results will appear here as soon as the Electoral Council publishes them.",
         ),
      ).toBeInTheDocument();
   });

   it("Renders the English infobox with the region type", () => {
      renderBox("Blaricum", "GEMEENTE", "en");

      expect(
         screen.getByText(
            "The counting results and certified election results for the municipality Blaricum will appear here as soon as the municipality Blaricum publishes them.",
         ),
      ).toBeInTheDocument();
   });
});
