import { describe, expect, it } from "vitest";
import { localeFromCookieHeader } from "@/i18n";

describe("localeFromCookieHeader", () => {
   it("reads the lang cookie among others", () => {
      expect(localeFromCookieHeader("theme=dark; lang=en; other=1")).toBe("en");
   });

   it("falls back to the source locale without a usable cookie", () => {
      expect(localeFromCookieHeader(undefined)).toBe("nl");
      expect(localeFromCookieHeader("theme=dark")).toBe("nl");
      expect(localeFromCookieHeader("lang=fr")).toBe("nl");
   });

   it("does not match cookies that merely end in lang", () => {
      expect(localeFromCookieHeader("xlang=en")).toBe("nl");
   });
});
