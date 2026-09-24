import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BreadcrumbItem, Breadcrumbs } from "@/components/Breadcrumbs";
import { renderWithProviders } from "../testUtils";

describe("Breadcrumbs", () => {
   it("lists the crumbs, marks the current page and hides the separators", () => {
      renderWithProviders(
         <Breadcrumbs>
            <BreadcrumbItem to="/ab2023">Waterschapsverkiezingen 2023</BreadcrumbItem>
            <BreadcrumbItem to="/ab2023/fout-melden">Fout melden</BreadcrumbItem>
         </Breadcrumbs>,
         { initialEntries: ["/ab2023/fout-melden"] },
      );

      const nav = screen.getByRole("navigation", { name: "Kruimelpad" });
      const items = within(nav).getAllByRole("listitem");
      expect(items).toHaveLength(3);
      expect(within(nav).getByRole("link", { name: "Fout melden" })).toHaveAttribute("aria-current", "page");
      expect(within(nav).getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
      expect(items[0]).toHaveTextContent(">");
      expect(within(items[0]).getByText(">")).toHaveAttribute("aria-hidden", "true");
   });
});
