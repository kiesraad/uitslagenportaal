import { useEffect, useRef } from "react";
import { useLocation } from "react-router";

/**
 * Moves focus to the page's h1 after a client-side navigation, so screen readers announce the new
 * page instead of staying on a link that is gone. Hash and query changes keep focus where it is.
 */
export function RouteFocus() {
   const { pathname } = useLocation();
   // Starts empty so the initial page load, where the browser already announces the page, is skipped.
   const previousPathname = useRef<string | null>(null);

   useEffect(() => {
      const previous = previousPathname.current;
      previousPathname.current = pathname;
      if (previous === null || previous === pathname) {
         return;
      }

      const heading = document.querySelector<HTMLElement>("main h1");
      if (heading) {
         heading.tabIndex = -1;
         heading.focus({ preventScroll: true });
      }
   }, [pathname]);

   return null;
}
