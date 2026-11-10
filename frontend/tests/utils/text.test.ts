import { describe, expect, it } from "vitest";
import { lowercaseFirst, uppercaseFirst } from "@/utils/text";

describe("lowercaseFirst", () => {
   it("lowercases only the first character", () => {
      expect(lowercaseFirst("Gemeente Utrecht")).toBe("gemeente Utrecht");
   });

   it("returns an empty string unchanged", () => {
      expect(lowercaseFirst("")).toBe("");
   });
});

describe("uppercaseFirst", () => {
   it("uppercases only the first character", () => {
      expect(uppercaseFirst("de gemeente Utrecht")).toBe("De gemeente Utrecht");
   });

   it("leaves an already capitalised label unchanged", () => {
      expect(uppercaseFirst("De Kiesraad")).toBe("De Kiesraad");
   });

   it("returns an empty string unchanged", () => {
      expect(uppercaseFirst("")).toBe("");
   });
});
