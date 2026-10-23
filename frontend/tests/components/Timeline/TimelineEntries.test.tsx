import { screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import type { ElectionDocument, Region, RegionSummary, TimelineVariant } from "@/api/types";
import { Timeline } from "@/components/Timeline/Timeline";
import type { TimelineEntryProps } from "@/components/Timeline/TimelineEntry";
import {
   CsbCheckTimelineEntry,
   CsbResultPublishTimelineEntry,
   GSBVoteCountTimelineEntry,
   HSBVoteCountTimelineEntry,
   SBVoteCountTimelineEntry,
} from "@/components/Timeline/TimelineEntry";
import { renderWithProviders } from "../../testUtils";

function summary(overrides: Partial<RegionSummary>): RegionSummary {
   return {
      id: 1,
      election_id: 1,
      parent_id: 0,
      region_number: "1",
      region_category: "GEMEENTE",
      region_name: "Utrecht",
      slug: "utrecht",
      ...overrides,
   };
}

function region(overrides: Partial<Region>): Region {
   return {
      region_name: "Utrecht",
      slug: "utrecht",
      vote_counts: [],
      region_category: "GEMEENTE",
      results_available_at: null,
      has_hsb: false,
      hsb: null,
      is_csb: false,
      csb: null,
      ...overrides,
   } as Region;
}

type Context = { variant?: TimelineVariant; region?: Region; documents?: ElectionDocument[]; locale?: "nl" | "en" };

function renderEntry(entry: ReactElement<TimelineEntryProps>, { locale, ...timelineProps }: Context = {}) {
   return renderWithProviders(
      <Timeline dates={[]} {...timelineProps}>
         {entry}
         {null}
      </Timeline>,
      { locale },
   );
}

describe("SBVoteCountTimelineEntry", () => {
   it.each<[TimelineVariant, string, RegExp]>([
      ["CSO", "Sneltelling in de stembureaus", /tellen de stembureaus alleen de stemmen per lijst/],
      ["DSO", "Telling in de stembureaus", /telt het stembureau de stemmen per lijst én per kandidaat/],
      ["DEFAULT", "Telling in de stembureaus", /Na het sluiten van de stembussen tellen de leden van het stembureau/],
   ])("has the %s title and body", (variant, title, body) => {
      renderEntry(<SBVoteCountTimelineEntry />, { variant });

      expect(screen.getByRole("heading", { level: 3, name: new RegExp(`^${title}`) })).toBeInTheDocument();
      expect(screen.getByText(body)).toBeInTheDocument();
   });

   it("falls back to the default texts without a variant", () => {
      renderEntry(<SBVoteCountTimelineEntry />);

      expect(screen.getByRole("heading", { level: 3, name: /^Telling in de stembureaus/ })).toBeInTheDocument();
   });
});

describe("GSBVoteCountTimelineEntry", () => {
   it("attaches the 510b document only", () => {
      const documents = [
         { file_type: "EML510b", url: "/api/documents/9/download/" },
         { file_type: "EML510d", url: "/api/documents/10/download/" },
      ] as ElectionDocument[];
      renderEntry(<GSBVoteCountTimelineEntry />, { documents });

      expect(screen.getByRole("link", { name: /^EML_NL tellingbestand 510b/ })).toHaveAttribute(
         "href",
         "/api/documents/9/download/",
      );
      expect(screen.queryByRole("link", { name: /^EML_NL tellingbestand 510d/ })).not.toBeInTheDocument();
   });
});

describe("CSB name in the timeline", () => {
   it("defaults to the Centraal Stembureau without a region", () => {
      renderEntry(<CsbResultPublishTimelineEntry />);

      expect(
         screen.getByRole("heading", { level: 3, name: /^Het Centraal Stembureau publiceert de uitslag/ }),
      ).toBeInTheDocument();
   });

   it("names the gemeente, capitalised, for a gemeente CSB", () => {
      renderEntry(<CsbCheckTimelineEntry />, { region: region({ csb: summary({ region_name: "Utrecht" }) }) });

      expect(screen.getByText(/^Gemeente Utrecht controleert de telresultaten/)).toBeInTheDocument();
   });

   it("uses the region itself when it is the CSB", () => {
      renderEntry(<CsbResultPublishTimelineEntry />, {
         region: region({ region_name: "Delfland", region_category: "WATERSCHAP", is_csb: true }),
      });

      expect(
         screen.getByRole("heading", { level: 3, name: /^Waterschap Delfland publiceert de uitslag/ }),
      ).toBeInTheDocument();
   });

   it("uses De Kiesraad for a STAAT CSB", () => {
      renderEntry(<CsbCheckTimelineEntry />, { region: region({ csb: summary({ region_category: "STAAT" }) }) });

      expect(screen.getByText(/^De Kiesraad controleert de telresultaten/)).toBeInTheDocument();
   });

   it("translates the name", () => {
      renderEntry(<CsbResultPublishTimelineEntry />, {
         region: region({ csb: summary({ region_name: "Utrecht" }) }),
         locale: "en",
      });

      expect(
         screen.getByRole("heading", { level: 3, name: /^The municipality of Utrecht publishes the results/ }),
      ).toBeInTheDocument();
   });
});

describe("HSBVoteCountTimelineEntry", () => {
   it("is hidden without a region", () => {
      renderEntry(<HSBVoteCountTimelineEntry />);

      expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
   });

   it("is hidden when the region has no HSB in the counting hierarchy", () => {
      renderEntry(<HSBVoteCountTimelineEntry />, {
         region: region({ has_hsb: false, hsb: summary({ region_category: "KIESKRING", region_name: "Noord" }) }),
      });

      expect(screen.queryByRole("heading", { level: 3 })).not.toBeInTheDocument();
   });

   it("names the HSB of a region that has one", () => {
      renderEntry(<HSBVoteCountTimelineEntry />, {
         region: region({ has_hsb: true, hsb: summary({ region_category: "KIESKRING", region_name: "Noord" }) }),
      });

      expect(screen.getByRole("heading", { level: 3, name: /^Optelling kieskring Noord/ })).toBeInTheDocument();
      expect(screen.getByText(/alle gemeenten in Kieskring Noord/)).toBeInTheDocument();
   });

   it("is shown for a kieskring itself", () => {
      renderEntry(<HSBVoteCountTimelineEntry />, {
         region: region({ region_name: "Zuid", region_category: "KIESKRING", has_hsb: false }),
      });

      expect(screen.getByRole("heading", { level: 3, name: /^Optelling kieskring Zuid/ })).toBeInTheDocument();
   });
});
