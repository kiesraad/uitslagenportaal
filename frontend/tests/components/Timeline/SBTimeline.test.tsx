import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SBTimeline } from "@/components/Timeline/SBTimeline";
import { renderWithProviders } from "../../testUtils";

describe("SBTimeline", () => {
   it("explains central counting for a CSO stembureau", () => {
      renderWithProviders(<SBTimeline variant="CSO" dates={[]} />);

      expect(screen.getByText(/Het stembureau doet een sneltelling per partij/)).toBeInTheDocument();
      expect(screen.getByText(/Dit wordt ook wel 'centraal tellen' genoemd/)).toBeInTheDocument();
   });

   it("explains decentral counting for a DSO stembureau", () => {
      renderWithProviders(<SBTimeline variant="DSO" dates={[]} />);

      expect(screen.getByText(/Het stembureau doet een uitgebreide telling/)).toBeInTheDocument();
      expect(screen.getByText(/telt het stembureau de stemmen per lijst én per kandidaat/)).toBeInTheDocument();
   });

   it("has no counting-method description by default", () => {
      renderWithProviders(<SBTimeline dates={[]} />);

      expect(screen.queryByText(/Het stembureau doet een/)).not.toBeInTheDocument();
      expect(
         screen.getByText(/Na het sluiten van de stembussen tellen de leden van het stembureau/),
      ).toBeInTheDocument();
      expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(4);
   });
});
