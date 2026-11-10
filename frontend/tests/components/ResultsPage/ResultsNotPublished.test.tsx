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
   it("Names the municipality with its type", () => {
      renderBox("Blaricum", "GEMEENTE");

      expect(screen.getByRole("heading", { name: /van gemeente Blaricum/ })).toBeInTheDocument();
      expect(
         screen.getByText(
            "De telresultaten en processen-verbaal van gemeente Blaricum zijn hier te zien zodra de gemeente ze publiceert.",
         ),
      ).toBeInTheDocument();
   });

   it("Names a waterschap and a polling station without an article", () => {
      const { unmount } = renderBox("Delfland", "WATERSCHAP");
      expect(screen.getByRole("heading", { name: /van waterschap Delfland/ })).toBeInTheDocument();
      unmount();

      renderBox("De Regenboog", "STEMBUREAU");
      expect(screen.getByRole("heading", { name: /van stembureau De Regenboog/ })).toBeInTheDocument();
   });

   it("Uses Nederland and De Kiesraad for a STAAT CSB", () => {
      renderBox("Nederland", "STAAT");

      expect(
         screen.getByRole("heading", { name: "De telresultaten van Nederland zijn nog niet gepubliceerd" }),
      ).toBeInTheDocument();
      expect(
         screen.getByText(
            /De telresultaten en processen-verbaal van Nederland zijn hier te zien zodra de Kiesraad ze publiceert./,
         ),
      ).toBeInTheDocument();
   });

   it("Renders the English infobox with the region type", () => {
      renderBox("Blaricum", "GEMEENTE", "en");

      expect(
         screen.getByText(
            "The counting results and certified election results for the municipality of Blaricum will appear here as soon as the municipality publishes them.",
         ),
      ).toBeInTheDocument();
   });
});
