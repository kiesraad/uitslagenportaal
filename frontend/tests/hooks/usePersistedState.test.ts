import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { usePersistedState } from "@/hooks/usePersistedState";

const KEY = "testKey";

const isNumber = (value: unknown): value is number => typeof value === "number";

beforeEach(() => {
   localStorage.clear();
});

describe("usePersistedState", () => {
   it("Returns the default when nothing is stored", () => {
      const { result } = renderHook(() => usePersistedState(KEY, 1));

      expect(result.current[0]).toBe(1);
   });

   it("Returns a previously stored value", () => {
      localStorage.setItem(KEY, JSON.stringify(5));
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(5);
   });

   it("Writes every update to storage, functional ones included", () => {
      const { result } = renderHook(() => usePersistedState(KEY, 1));

      act(() => result.current[1](2));
      expect(localStorage.getItem(KEY)).toBe("2");

      act(() => result.current[1]((current) => current + 1));
      expect(result.current[0]).toBe(3);
      expect(localStorage.getItem(KEY)).toBe("3");
   });

   it("Falls back to the default on unparsable JSON", () => {
      localStorage.setItem(KEY, "{not json");
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(1);
   });

   it("Falls back to the default on a value the guard rejects", () => {
      localStorage.setItem(KEY, JSON.stringify("five"));
      const { result } = renderHook(() => usePersistedState(KEY, 1, isNumber));

      expect(result.current[0]).toBe(1);
   });
});
