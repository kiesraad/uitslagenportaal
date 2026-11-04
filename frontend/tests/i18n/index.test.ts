import { beforeEach, describe, expect, it, vi } from "vitest";
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

describe("getLoadedI18n", () => {
   // A fresh module per test, so no instance carries a catalogue over from another test.
   let i18nModule: typeof import("@/i18n");
   beforeEach(async () => {
      vi.resetModules();
      i18nModule = await import("@/i18n");
   });

   it("returns the requested instance when its catalogue is loaded", () => {
      const { getI18n, getLoadedI18n } = i18nModule;
      getI18n("nl").loadAndActivate({ locale: "nl", messages: {} });
      getI18n("en").loadAndActivate({ locale: "en", messages: {} });

      expect(getLoadedI18n("en")).toBe(getI18n("en"));
   });

   it("falls back to a loaded instance when the requested catalogue is not loaded", () => {
      const { getI18n, getLoadedI18n } = i18nModule;
      getI18n("en").loadAndActivate({ locale: "en", messages: {} });

      expect(getLoadedI18n("nl")).toBe(getI18n("en"));
   });

   it("returns the requested instance when no catalogue is loaded at all", () => {
      const { getI18n, getLoadedI18n } = i18nModule;

      expect(getLoadedI18n("nl")).toBe(getI18n("nl"));
   });
});
