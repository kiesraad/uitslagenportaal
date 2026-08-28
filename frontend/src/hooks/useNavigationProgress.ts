import { useEffect, useRef, useState } from "react";

// Most navigations resolve from the warmed query cache within a few dozen milliseconds.
// Holding off the first paint keeps the bar from flashing on those.
const SHOW_DELAY_MS = 150;
// Stays under the bar's own `duration-300` transition, to keep the animation smooth.
const TRICKLE_INTERVAL_MS = 200;
// Covers that same transition, so the bar reaches the end of its track before it fades.
const EXIT_DURATION_MS = 350;

const INITIAL_PROGRESS = 0.08;
const TRICKLE_CEILING = 0.99;
const TRICKLE_FRACTION = 0.1;

// Each step closes a fixed fraction of the distance still to run, so the bar decelerates
// smoothly and approaches the ceiling without ever arriving: only a resolved navigation
// may complete it, or it promises a page that has not landed.
function trickle(progress: number): number {
   return progress + (TRICKLE_CEILING - progress) * TRICKLE_FRACTION;
}

/**
 * Pacing for the navigation progress bar: a delayed start, a decelerating trickle while
 * the navigation is pending, and a completed bar that lingers long enough to animate out.
 */
export function useNavigationProgress(isNavigating: boolean) {
   const [progress, setProgress] = useState(0);
   const [isVisible, setIsVisible] = useState(false);
   // Whether the bar was ever painted for the current navigation. Reading `isVisible`
   // instead would add it to the dependencies below, so the effect would re-run on its
   // own update and restart the trickle halfway.
   const isShown = useRef(false);

   useEffect(() => {
      if (isNavigating) {
         let interval: ReturnType<typeof setInterval> | undefined;

         // Reset the progress bar as it's left at non-0 last time it was shown
         setProgress(0);

         const delay = setTimeout(() => {
            isShown.current = true;
            setIsVisible(true);
            setProgress(INITIAL_PROGRESS);
            interval = setInterval(() => setProgress(trickle), TRICKLE_INTERVAL_MS);
         }, SHOW_DELAY_MS);

         return () => {
            clearTimeout(delay);
            clearInterval(interval);
         };
      }

      if (!isShown.current) return;
      isShown.current = false;

      setProgress(1);
      // The bar is left at full width while it fades and reset next time it's shown
      const hide = setTimeout(() => setIsVisible(false), EXIT_DURATION_MS);

      return () => clearTimeout(hide);
   }, [isNavigating]);

   return { isVisible, progress };
}
