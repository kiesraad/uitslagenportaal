import { describe, expect, it } from "vitest";
import { readCookie, writeCookie } from "@/utils/cookies";

describe("readCookie", () => {
   it("reads a cookie among others in a header", () => {
      expect(readCookie("lang", "theme=dark; lang=en; other=1")).toBe("en");
   });

   it("returns null for a missing cookie or one whose name merely ends in it", () => {
      expect(readCookie("lang", "theme=dark")).toBeNull();
      expect(readCookie("lang", "xlang=en")).toBeNull();
   });
});

describe("writeCookie", () => {
   it("round-trips a value with characters that need encoding", () => {
      writeCookie("setting", '{"a":"b; c"}');

      expect(readCookie("setting")).toBe('{"a":"b; c"}');
   });
});
