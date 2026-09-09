import { screen } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it } from "vitest";
import type { ElectionConfig, Region } from "@/api/types";
import { RegionList } from "@/components/ListPage/RegionList";
import { renderWithProviders } from "../../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00",
   csb_type: "WATERSCHAP",
   has_hsb: false,
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

const zoetermeer: Region = {
   region_name: "Zoetermeer",
   slug: "zoetermeer",
   vote_counts: [],
   region_category: "GEMEENTE",
   results_available_at: null,
};

function renderRegionList(props: Partial<ComponentProps<typeof RegionList>> = {}, locale: "nl" | "en" = "nl") {
   return renderWithProviders(
      <RegionList electionConfig={electionConfig} regions={[]} regionCategory="GEMEENTE" {...props} />,
      { locale },
   );
}

describe("RegionList", () => {
   it("replaces search and the A-to-Z heading with a placeholder when the election-level list is empty", () => {
      renderRegionList({ emptyPlaceholder: true });

      expect(screen.getByRole("heading", { name: "De gemeenten zijn nog niet beschikbaar" })).toBeInTheDocument();
      expect(
         screen.getByText("De lijst verschijnt hier zodra de resultaten worden gepubliceerd."),
      ).toBeInTheDocument();
      expect(screen.queryByLabelText("Zoek gemeente")).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Vind een gemeente van A tot Z" })).not.toBeInTheDocument();
   });

   it("names the placeholder after the region type", () => {
      renderRegionList({ emptyPlaceholder: true, regionCategory: "WATERSCHAP" });

      expect(screen.getByRole("heading", { name: "De waterschappen zijn nog niet beschikbaar" })).toBeInTheDocument();
   });

   it("keeps search and the A-to-Z heading when the empty placeholder is off", () => {
      renderRegionList();

      expect(screen.getByLabelText("Zoek gemeente")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Vind een gemeente van A tot Z" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "De gemeenten zijn nog niet beschikbaar" })).not.toBeInTheDocument();
   });

   it("shows the list when regions are present, even with the empty placeholder on", () => {
      renderRegionList({ emptyPlaceholder: true, regions: [zoetermeer] });

      expect(screen.getByLabelText("Zoek gemeente")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Vind een gemeente van A tot Z" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Zoetermeer/ })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "De gemeenten zijn nog niet beschikbaar" })).not.toBeInTheDocument();
   });
});
