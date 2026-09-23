import { Trans, useLingui } from "@lingui/react/macro";
import { Link } from "react-router";
import { NavigationProgressBar } from "./NavigationProgressBar";

export function Header() {
   const { t } = useLingui();
   return (
      <>
         <a
            href="#main-content"
            className="sr-only z-200 bg-white px-4 py-3 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
         >
            <Trans>Naar hoofdinhoud</Trans>
         </a>
         <header className="header">
            <div className="header-inner flex flex-row items-end">
               <Link to="/" className="header-logo">
                  <img src="/kiesraad_logo.png" alt={t`Kiesraad, naar home`} className="header-logo-img" />
               </Link>
            </div>
         </header>
         <NavigationProgressBar />
      </>
   );
}
