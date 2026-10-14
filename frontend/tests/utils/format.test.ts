import { i18n } from "@lingui/core";
import { beforeEach, describe, expect, it } from "vitest";
import { formatDate, formatTimelineDate } from "@/utils/format";
import { activateLocale } from "../testUtils";

// 20:00 UTC is 21:00 in Amsterdam in winter.
const ISO_DATE = "2025-12-08T20:00:00Z";

describe("formatDate", () => {
   beforeEach(() => activateLocale("nl"));

   it("joins date and time with a dash by default", () => {
      expect(formatDate(i18n, "nl", ISO_DATE)).toBe("8 december 2025 - 21:00");
   });

   it.each([
      ["dash", "8 december - 21:00"],
      ["at", "8 december om 21:00"],
      ["after", "8 december na 21:00"],
      ["until", "8 december tot 21:00"],
      ["none", "8 december 21:00"],
   ] as const)("joins with the %s delimiter", (delimiter, expected) => {
      expect(formatDate(i18n, "nl", ISO_DATE, { delimiter, withYear: false })).toBe(expected);
   });

   it("translates the delimiter", () => {
      activateLocale("en");
      expect(formatDate(i18n, "en", ISO_DATE, { delimiter: "at" })).toBe("8 December 2025 at 21:00");
   });

   it("returns the input when it cannot be parsed", () => {
      expect(formatDate(i18n, "nl", "not a date")).toBe("not a date");
   });
});

describe("formatTimelineDate", () => {
   beforeEach(() => activateLocale("nl"));

   it.each([
      ["from", "8 december na 21:00"],
      ["until", "8 december tot 21:00"],
      ["expected", "Verwacht: 8 december om 21:00"],
   ] as const)("formats the %s qualifier", (qualifier, expected) => {
      expect(formatTimelineDate(i18n, "nl", { event: "sb_vote_count", date: ISO_DATE, qualifier })).toBe(expected);
   });
});
