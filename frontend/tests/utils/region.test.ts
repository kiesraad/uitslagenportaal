import { describe, expect, it } from "vitest";
import type { RegionSummary } from "@/api/types";
import { formatStationLabel, getCsbCrumb, getRegionLabels } from "@/utils/region";

describe("formatStationLabel", () => {
   it("prefixes a zero-padded station number", () => {
      expect(formatStationLabel("De Regenboog", 1)).toBe("001 - De Regenboog");
      expect(formatStationLabel("De Regenboog", 12)).toBe("012 - De Regenboog");
   });

   it("leaves numbers of three digits or more unpadded", () => {
      expect(formatStationLabel("De Regenboog", 100)).toBe("100 - De Regenboog");
      expect(formatStationLabel("De Regenboog", 1000)).toBe("1000 - De Regenboog");
   });

   it("returns the name when there is no station number", () => {
      expect(formatStationLabel("Borsele")).toBe("Borsele");
      expect(formatStationLabel("Borsele", null)).toBe("Borsele");
   });
});

describe("getCsbCrumb", () => {
   const csb = { region_name: "Delfland", slug: "delfland" } as RegionSummary;

   it("links to the municipality list of the CSB", () => {
      expect(getCsbCrumb({ csb }, "ws2026")).toEqual({
         href: expect.stringContaining("delfland"),
         label: "Delfland",
      });
   });

   it("is null without a CSB", () => {
      expect(getCsbCrumb({ csb: null }, "ws2026")).toBeNull();
      expect(getCsbCrumb(undefined, "ws2026")).toBeNull();
   });
});

describe("getRegionLabels", () => {
   it("has a separate CSB name only for STAAT", () => {
      expect(getRegionLabels("STAAT").csbName).toBeDefined();
      expect(getRegionLabels("GEMEENTE").csbName).toBeUndefined();
   });
});
