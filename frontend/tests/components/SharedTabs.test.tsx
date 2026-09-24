import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SharedTabs from "@/components/SharedTabs";
import { renderWithProviders } from "../testUtils";

describe("SharedTabs", () => {
   it("marks the link to the current page", () => {
      renderWithProviders(
         <SharedTabs
            tabs={[
               { label: "Per stembureau", value: "/gemeente" },
               { label: "Hele gemeente", value: "/gemeente/resultaten" },
            ]}
         />,
         { initialEntries: ["/gemeente/resultaten"] },
      );

      expect(screen.getByRole("navigation", { name: "Subnavigatie" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Hele gemeente" })).toHaveAttribute("aria-current", "page");
      expect(screen.getByRole("link", { name: "Per stembureau" })).not.toHaveAttribute("aria-current");
   });
});
