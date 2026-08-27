import { useNavigation } from "react-router";
import { twMerge } from "tailwind-merge";
import { useNavigationProgress } from "@/hooks/useNavigationProgress";

/**
 * Slim bar below the header tracking a pending router navigation. It sticks to the top of
 * the viewport once the header scrolls away, and always occupies its 3px so that appearing
 * shifts nothing. Decorative only: pages announce their own loading state.
 */
export function NavigationProgressBar() {
   const navigation = useNavigation();
   const { isVisible, progress } = useNavigationProgress(Boolean(navigation.location));

   return (
      <div
         className={twMerge(
            "sticky top-0 z-100 h-0.75 -mb-0.75 shrink-0 pointer-events-none opacity-0 transition-opacity duration-200",
            isVisible && "opacity-100",
         )}
         aria-hidden="true"
      >
         <div
            className="h-full origin-left bg-blue-400 shadow-blue-700/50 shadow-md rounded-full will-change-transform transition-transform duration-300 ease-in-out motion-reduce:transition-none"
            style={{ transform: `scaleX(${progress})` }}
         />
      </div>
   );
}
