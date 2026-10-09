import { describe, expect, it } from "vitest";
import { formatStationLabel } from "@/utils/region";

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
