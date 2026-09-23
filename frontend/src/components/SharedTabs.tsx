import { useLingui } from "@lingui/react/macro";
import { Link, matchPath, useLocation } from "react-router";
import { twMerge } from "tailwind-merge";

type Props = {
   tabs: {
      label: string;
      value: string;
      activePatterns?: string[];
   }[];
};

// Links between views of the same region, not ARIA tabs: each one loads its own page.
export default function SharedTabs({ tabs }: Props) {
   const location = useLocation();
   const { t } = useLingui();

   return (
      <nav className="tabs" aria-label={t`Weergave`}>
         {tabs.map((tab) => {
            const patterns = tab.activePatterns ?? [tab.value];
            const isActive = patterns.some((pattern) =>
               matchPath({ path: pattern, end: !pattern.endsWith("*") }, location.pathname),
            );

            return (
               <Link
                  key={tab.value}
                  to={tab.value}
                  className={twMerge("tab text-lg", isActive && "active")}
                  aria-current={isActive ? "page" : undefined}
               >
                  {tab.label}
               </Link>
            );
         })}
      </nav>
   );
}
