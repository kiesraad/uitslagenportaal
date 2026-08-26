import { Link } from "react-router";
import { NavigationProgressBar } from "./NavigationProgressBar";

export function Header() {
   return (
      <>
         <header className="header">
            <div className="header-inner flex flex-row items-end">
               <Link to="/" className="header-logo">
                  <img src="/kiesraad_logo.png" alt="Kiesraad" className="header-logo-img" />
               </Link>
            </div>
         </header>
         <NavigationProgressBar />
      </>
   );
}
