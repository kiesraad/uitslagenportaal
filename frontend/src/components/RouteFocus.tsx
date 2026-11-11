import { useContext, useEffect } from "react";
import { UNSAFE_DataRouterContext, useLocation } from "react-router";

// The last pathname seen per router, so separate routers (one per test) share no state. The root Layout,
// and with it RouteFocus, remounts when the page swaps with the error boundary or the loading fallback.
const lastPathnames = new WeakMap<object, string>();

/**
 * Moves focus to the page's h1 after a client-side navigation, so screen readers announce the new
 * page instead of staying on a link that is gone. Hash and query changes keep focus where it is.
 */
export function RouteFocus() {
   const { pathname } = useLocation();
   const router = useContext(UNSAFE_DataRouterContext)?.router;

   useEffect(() => {
      if (!router) {
         return;
      }

      // Unset on the initial page load, where the browser already announces the page.
      const previous = lastPathnames.get(router);
      lastPathnames.set(router, pathname);
      if (previous === undefined || previous === pathname) {
         return;
      }

      const heading = document.querySelector<HTMLElement>("main h1");
      if (heading) {
         heading.tabIndex = -1;
         heading.focus({ preventScroll: true });
      }
   }, [pathname, router]);

   return null;
}
