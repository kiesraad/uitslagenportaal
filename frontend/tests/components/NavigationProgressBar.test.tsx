import { act, fireEvent, render, screen } from "@testing-library/react";
import { createRoutesStub, useRevalidator } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NavigationProgressBar } from "@/components/NavigationProgressBar";

// Mirrors the pacing of useNavigationProgress, which owns the timings themselves.
const SHOW_DELAY_MS = 150;
const EXIT_DURATION_MS = 350;

/**
 * Mounts the bar in a router whose loader hangs until released, so a revalidation — what a
 * language switch performs — can be held open for as long as the assertions need.
 */
function renderBar() {
   let releaseLoader = () => {};
   const loading = new Promise<void>((resolve) => {
      releaseLoader = resolve;
   });

   function Chrome() {
      const revalidator = useRevalidator();

      return (
         <div data-testid="chrome">
            <NavigationProgressBar />
            <button type="button" onClick={() => void revalidator.revalidate()}>
               revalidate
            </button>
         </div>
      );
   }

   const Stub = createRoutesStub([
      {
         id: "root",
         path: "*",
         loader: async () => {
            await loading;
            return null;
         },
         Component: Chrome,
      },
   ]);

   // Hydrated, so the loader runs for the revalidation rather than for the first render.
   render(<Stub hydrationData={{ loaderData: { root: null } }} />);

   return {
      releaseLoader: () => releaseLoader(),
      isVisible: () => screen.getByTestId("chrome").firstElementChild?.className.includes("opacity-100"),
   };
}

beforeEach(() => {
   vi.useFakeTimers();
});

afterEach(() => {
   vi.useRealTimers();
});

describe("NavigationProgressBar", () => {
   it("Runs for a revalidation, which is what a language switch performs", async () => {
      const { releaseLoader, isVisible } = renderBar();

      expect(isVisible()).toBe(false);

      fireEvent.click(screen.getByRole("button", { name: "revalidate" }));
      act(() => {
         vi.advanceTimersByTime(SHOW_DELAY_MS);
      });
      expect(isVisible()).toBe(true);

      await act(async () => {
         releaseLoader();
      });
      act(() => {
         vi.advanceTimersByTime(EXIT_DURATION_MS);
      });
      expect(isVisible()).toBe(false);
   });
});
