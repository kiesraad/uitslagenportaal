import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePersistedState } from "@/hooks/usePersistedState";
import { readCookie, writeCookie } from "@/utils/cookies";

const KEY = "testKey";

const isNumber = (value: unknown): value is number => typeof value === "number";

describe("usePersistedState", () => {
   it("Returns the default when nothing is stored", () => {
      const { result } = renderHook(() => usePersistedState(KEY, 1));

      expect(result.current[0]).toBe(1);
   });

   it("Returns a previously stored value", () => {
      writeCookie(KEY, JSON.stringify(5));
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(5);
   });

   it("Renders the default first and keeps the stored value in storage", () => {
      writeCookie(KEY, JSON.stringify(5));
      const renders: number[] = [];
      renderHook(() => {
         const state = usePersistedState(KEY, 1, isNumber);
         renders.push(state[0]);
         return state;
      });

      // The first render matches markup rendered without a browser; the stored value follows.
      expect(renders[0]).toBe(1);
      expect(renders.at(-1)).toBe(5);
      expect(readCookie(KEY)).toBe("5");
   });

   it("Writes every update to storage, functional ones included", () => {
      const { result } = renderHook(() => usePersistedState(KEY, 1));

      act(() => result.current[1](2));
      expect(readCookie(KEY)).toBe("2");

      act(() => result.current[1]((current) => current + 1));
      expect(result.current[0]).toBe(3);
      expect(readCookie(KEY)).toBe("3");
   });

   it("Falls back to the default on unparsable JSON", () => {
      writeCookie(KEY, "{not json");
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(1);
   });

   it("Falls back to the default on a value the guard rejects", () => {
      writeCookie(KEY, JSON.stringify("five"));
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(1);
   });
});
