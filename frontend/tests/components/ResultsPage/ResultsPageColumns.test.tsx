import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultsPageColumns from "@/components/ResultsPage/ResultsPageColumns";
import { renderWithProviders } from "../../testUtils";

describe("ResultsPageColumns", () => {
   it("Shows the proces-verbaal stub on the Vite dev server", () => {
      renderWithProviders(
         <ResultsPageColumns>
            <p>Results</p>
         </ResultsPageColumns>,
         {
            initialEntries: ["/ws2023/gsb/lisserdam"],
            path: "/:electionConfigSlug/*",
         },
      );

      expect(screen.getByText("Results")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });
});
