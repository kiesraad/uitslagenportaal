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
   const ws = { slug: "ws2026", single_csb: null };

   it("links to the municipality list of the CSB", () => {
      expect(getCsbCrumb({ csb }, ws)).toEqual({
         href: "/ws2026/csb/delfland",
         label: "Delfland",
      });
   });

   it("links to the CSB tab when the election has a single CSB", () => {
      const nederland = { region_name: "Nederland", slug: "nederland" } as RegionSummary;
      const ep = { slug: "ep2024", single_csb: { region_name: "Nederland", slug: "nederland" } };
      expect(getCsbCrumb({ csb: nederland }, ep)).toEqual({ href: "/ep2024/csb", label: "Nederland" });
   });

   it("is null without a CSB", () => {
      expect(getCsbCrumb({ csb: null }, ws)).toBeNull();
      expect(getCsbCrumb(undefined, ws)).toBeNull();
   });
});

describe("getRegionLabels", () => {
   it("has a separate CSB name only for STAAT", () => {
      expect(getRegionLabels("STAAT").csbName).toBeDefined();
      expect(getRegionLabels("GEMEENTE").csbName).toBeUndefined();
   });
});
