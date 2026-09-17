import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultsSourceBox from "@/components/ResultsPage/ResultsSourceBox";
import { renderWithProviders } from "../../testUtils";

function renderBox(locale: "nl" | "en" = "nl") {
   return renderWithProviders(<ResultsSourceBox />, {
      locale,
      initialEntries: ["/ws2023/gsb/lisserdam"],
      path: "/:electionConfigSlug/*",
   });
}

describe("ResultsSourceBox", () => {
   it("Shows the stub proces-verbaal preview and view link", () => {
      renderBox();

      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
      expect(screen.getByRole("img", { name: "Voorbeeld van een proces-verbaal" })).toHaveAttribute(
         "src",
         "/images/results_image.png",
      );
      expect(screen.getByRole("link", { name: /Bekijk het proces-verbaal/ })).toHaveAttribute(
         "href",
         "/images/results_image.png",
      );
      expect(screen.getByRole("link", { name: /Meld een fout of iets dat niet klopt/ })).toHaveAttribute(
         "href",
         "/ws2023/fout-melden",
      );
   });

   it("Renders the source box in English when that locale is active", () => {
      renderBox("en");

      expect(screen.getByRole("heading", { name: "Where do these counting results come from?" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /View the certified election results/ })).toBeInTheDocument();
   });
});
