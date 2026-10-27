import { screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";
import type { ElectionDocument, Region } from "@/api/types";
import { CSBTimeline } from "@/components/Timeline/CSBTimeline";
import { GenericTimeline } from "@/components/Timeline/GenericTimeline";
import { GSBTimeline } from "@/components/Timeline/GSBTimeline";
import { HSBTimeline } from "@/components/Timeline/HSBTimeline";
import { SBTimeline } from "@/components/Timeline/SBTimeline";
import { renderWithProviders } from "../../testUtils";

const kieskring = {
   region_name: "Noord",
   region_category: "KIESKRING",
   has_hsb: true,
   hsb: null,
   is_csb: false,
   csb: null,
} as Region;
const gemeente = {
   ...kieskring,
   region_name: "Utrecht",
   region_category: "GEMEENTE",
   hsb: { region_name: "Noord" },
} as Region;
const gemeenteWithoutHsb = { ...gemeente, has_hsb: false } as Region;

// Entries are listed latest step first.
function steps(ui: ReactElement) {
   renderWithProviders(ui);
   return screen
      .getAllByRole("heading", { level: 3 })
      .map((heading) => (heading.textContent ?? "").replace(/, (afgerond|bezig|nog niet gestart)$/, ""));
}

describe("GenericTimeline", () => {
   it("lists the generic steps without an HSB-specific entry", () => {
      expect(steps(<GenericTimeline dates={[]} />)).toEqual([
         "Het Centraal Stembureau publiceert de uitslag",
         "Centraal Stembureau controleert",
         "Optelling per kieskring",
         "Optelling per gemeente",
         "Telling in de stembureaus",
      ]);
   });
});

describe("CSBTimeline", () => {
   it("skips the HSB entry when no HSB takes part", () => {
      expect(steps(<CSBTimeline dates={[]} region={gemeenteWithoutHsb} />)).toEqual([
         "Het Centraal Stembureau publiceert de uitslag",
         "Centraal Stembureau controleert",
         "Optelling per gemeente",
         "Telling in de stembureaus",
      ]);
   });

   it("includes the HSB entry when the region has one", () => {
      expect(steps(<CSBTimeline dates={[]} region={gemeente} />)).toContain("Optelling kieskring Noord");
   });

   it("passes the 520 document to the CSB check entry", () => {
      const documents = [{ file_type: "EML520", url: "/api/documents/4/download/" }] as ElectionDocument[];
      renderWithProviders(<CSBTimeline dates={[]} documents={documents} />);

      expect(screen.getByRole("link", { name: /^EML_NL resultaatbestand 520/ })).toBeInTheDocument();
   });
});

describe("HSBTimeline", () => {
   it("names its own kieskring", () => {
      expect(steps(<HSBTimeline dates={[]} region={kieskring} />)).toEqual([
         "Het Centraal Stembureau publiceert de uitslag",
         "Centraal Stembureau controleert",
         "Optelling kieskring Noord",
         "Optelling per gemeente",
         "Telling in de stembureaus",
      ]);
   });
});

describe("GSBTimeline", () => {
   it("shows the kieskring of the gemeente and the variant description", () => {
      const result = steps(<GSBTimeline variant="DSO" dates={[]} region={gemeente} />);

      expect(result).toContain("Optelling kieskring Noord");
      expect(screen.getByText(/Het stembureau doet een uitgebreide telling/)).toBeInTheDocument();
   });

   it("has no variant description by default", () => {
      steps(<GSBTimeline dates={[]} region={gemeenteWithoutHsb} />);

      expect(screen.queryByText(/Het stembureau doet een/)).not.toBeInTheDocument();
   });

   it("passes documents to its entries", () => {
      const documents = [{ file_type: "EML510b", url: "/api/documents/3/download/" }] as ElectionDocument[];
      renderWithProviders(<GSBTimeline dates={[]} documents={documents} />);

      expect(screen.getByRole("link", { name: /^EML_NL tellingbestand 510b/ })).toBeInTheDocument();
   });
});

describe("SBTimeline", () => {
   it("adds the candidate count for a CSO stembureau", () => {
      expect(steps(<SBTimeline variant="CSO" dates={[]} region={gemeenteWithoutHsb} />)).toEqual([
         "Het Centraal Stembureau publiceert de uitslag",
         "Centraal Stembureau controleert",
         "Optelling per gemeente",
         "Telling per lijst en kandidaat",
         "Sneltelling in de stembureaus",
      ]);
   });

   it("has no candidate count for a DSO stembureau", () => {
      expect(steps(<SBTimeline variant="DSO" dates={[]} />)).not.toContain("Telling per lijst en kandidaat");
   });
});
