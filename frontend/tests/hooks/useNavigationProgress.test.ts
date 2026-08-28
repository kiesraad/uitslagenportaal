import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useNavigationProgress } from "@/hooks/useNavigationProgress";

const SHOW_DELAY_MS = 150;
const TRICKLE_INTERVAL_MS = 200;
const EXIT_DURATION_MS = 350;
const TRICKLE_CEILING = 0.99;

function renderProgress(isNavigating: boolean) {
   return renderHook((props: { isNavigating: boolean }) => useNavigationProgress(props.isNavigating), {
      initialProps: { isNavigating },
   });
}

function advance(ms: number) {
   act(() => {
      vi.advanceTimersByTime(ms);
   });
}

beforeEach(() => {
   vi.useFakeTimers();
});

afterEach(() => {
   vi.useRealTimers();
});

describe("useNavigationProgress", () => {
   it("Never paints for a navigation that resolves inside the show delay", () => {
      const { result, rerender } = renderProgress(true);

      advance(SHOW_DELAY_MS - 50);
      expect(result.current.isVisible).toBe(false);

      rerender({ isNavigating: false });
      advance(EXIT_DURATION_MS + TRICKLE_INTERVAL_MS);

      expect(result.current.isVisible).toBe(false);
      expect(result.current.progress).toBe(0);
   });

   it("Appears once the delay has passed and trickles while the navigation is pending", () => {
      const { result } = renderProgress(true);

      advance(SHOW_DELAY_MS);
      expect(result.current.isVisible).toBe(true);
      expect(result.current.progress).toBe(0.08);

      advance(TRICKLE_INTERVAL_MS);
      expect(result.current.progress).toBeGreaterThan(0.08);
   });

   it("Stops short of the end however long the navigation takes", () => {
      const { result } = renderProgress(true);

      advance(SHOW_DELAY_MS + TRICKLE_INTERVAL_MS * 100);

      expect(result.current.progress).toBeLessThan(TRICKLE_CEILING);
   });

   it("Completes the bar when the navigation resolves, then hides it", () => {
      const { result, rerender } = renderProgress(true);

      advance(SHOW_DELAY_MS + TRICKLE_INTERVAL_MS);
      rerender({ isNavigating: false });

      expect(result.current.progress).toBe(1);
      expect(result.current.isVisible).toBe(true);

      advance(EXIT_DURATION_MS);
      expect(result.current.isVisible).toBe(false);
      // Left at full width behind the fade; the next navigation is what resets it.
      expect(result.current.progress).toBe(1);
   });

   it("Runs again for the next navigation", () => {
      const { result, rerender } = renderProgress(true);

      advance(SHOW_DELAY_MS);
      rerender({ isNavigating: false });
      advance(EXIT_DURATION_MS);
      expect(result.current.isVisible).toBe(false);

      rerender({ isNavigating: true });
      advance(SHOW_DELAY_MS);

      expect(result.current.isVisible).toBe(true);
      expect(result.current.progress).toBe(0.08);
   });
});
