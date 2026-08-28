import { useNavigation, useRevalidator } from "react-router";
import { twMerge } from "tailwind-merge";
import { useNavigationProgress } from "@/hooks/useNavigationProgress";

/**
 * Slim bar below the header tracking pending router work. It sticks to the top of
 * the viewport once the header scrolls away, and always occupies its 3px so that appearing
 * shifts nothing. Decorative only: pages announce their own loading state.
 */
export function NavigationProgressBar() {
   // navigation is loading a new page, revalidation is re-running a loader for the current page
   // The latter mainly happens when changing locale
   const navigation = useNavigation();
   const revalidator = useRevalidator();
   const { isVisible, progress } = useNavigationProgress(
      Boolean(navigation.location) || revalidator.state === "loading",
   );

   return (
      <div
         className={twMerge(
            "sticky top-0 z-100 h-0.75 -mb-0.75 shrink-0 pointer-events-none opacity-0 transition-opacity duration-200",
            isVisible && "opacity-100",
         )}
         aria-hidden="true"
      >
         <div
            className={twMerge(
               "h-full origin-left bg-blue-400 shadow-blue-700/50 shadow-md rounded-full",
               // Only animate transforms when visible
               isVisible && "transition-transform duration-300 ease-in-out will-change-transform",
               "motion-reduce:transition-none",
            )}
            style={{ transform: `scaleX(${progress})` }}
         />
      </div>
   );
}
