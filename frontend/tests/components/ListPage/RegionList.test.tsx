import { fireEvent, screen } from "@testing-library/react";
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
   category: "WS",
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
      expect(screen.getByText("De lijst verschijnt hier zodra de resultaten worden gepubliceerd.")).toBeInTheDocument();
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

   it("prefixes stembureau search suggestions with a zero-padded station number", () => {
      const stations: Region[] = [
         {
            region_name: "De Regenboog",
            slug: "sb1-de-regenboog",
            vote_counts: [],
            region_category: "STEMBUREAU",
            results_available_at: null,
            station_number: 1,
         },
         {
            region_name: "De Regenboog",
            slug: "sb2-de-regenboog",
            vote_counts: [],
            region_category: "STEMBUREAU",
            results_available_at: null,
            station_number: 2,
         },
      ];
      renderRegionList({ regionCategory: "STEMBUREAU", regions: stations, parentRegionSlug: "borsele" });

      fireEvent.change(screen.getByRole("searchbox"), { target: { value: "regenboog" } });

      expect(screen.getByRole("option", { name: "001 - De Regenboog" })).toBeInTheDocument();
      expect(screen.getByRole("option", { name: "002 - De Regenboog" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "1De Regenboog" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "2De Regenboog" })).toBeInTheDocument();
   });

   it("finds a stembureau by its padded station number", () => {
      const stations: Region[] = [
         {
            region_name: "De Regenboog",
            slug: "sb1-de-regenboog",
            vote_counts: [],
            region_category: "STEMBUREAU",
            results_available_at: null,
            station_number: 1,
         },
         {
            region_name: "Basisschool de Piratenboot",
            slug: "sb3-piratenboot",
            vote_counts: [],
            region_category: "STEMBUREAU",
            results_available_at: null,
            station_number: 3,
         },
      ];
      renderRegionList({ regionCategory: "STEMBUREAU", regions: stations, parentRegionSlug: "borsele" });

      fireEvent.change(screen.getByRole("searchbox"), { target: { value: "001" } });

      expect(screen.getByRole("option", { name: "001 - De Regenboog" })).toBeInTheDocument();
      expect(screen.queryByRole("option", { name: "003 - Basisschool de Piratenboot" })).not.toBeInTheDocument();
   });
});
