import { act, renderHook } from "@testing-library/react";
import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { usePersistedState } from "@/hooks/usePersistedState";
import { readCookie, writeCookie } from "@/utils/cookies";

const KEY = "testKey";

const isNumber = (value: unknown): value is number => typeof value === "number";

function Value() {
   return usePersistedState(KEY, 1, isNumber)[0];
}

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

   it("Renders a stored value from the first render", () => {
      writeCookie(KEY, JSON.stringify(5));
      const renders: number[] = [];
      renderHook(() => {
         const state = usePersistedState(KEY, 1, isNumber);
         renders.push(state[0]);
         return state;
      });

      expect(renders[0]).toBe(5);
   });

   it("Keeps an object value and the setter stable between renders", () => {
      writeCookie(KEY, JSON.stringify({ count: 5 }));
      const { result, rerender } = renderHook(() => usePersistedState(KEY, { count: 1 }));
      const [firstValue, firstSetter] = result.current;

      rerender();
      expect(result.current[0]).toBe(firstValue);
      expect(result.current[1]).toBe(firstSetter);
   });

   it("Renders the default without a browser", () => {
      writeCookie(KEY, JSON.stringify(5));

      expect(renderToString(createElement(Value))).toBe("1");
   });

   it("Does not write a cookie until a value is set", () => {
      renderHook(() => usePersistedState(KEY, 1));

      expect(readCookie(KEY)).toBeNull();
   });

   it("Updates every component reading the same key", () => {
      const first = renderHook(() => usePersistedState(KEY, 1));
      const second = renderHook(() => usePersistedState(KEY, 1));

      act(() => first.result.current[1](2));
      expect(second.result.current[0]).toBe(2);
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
