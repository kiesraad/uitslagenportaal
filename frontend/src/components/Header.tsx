import { faCircleNotch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link, useNavigation } from "react-router";
import { twMerge } from "tailwind-merge";

export function Header() {
   const navigation = useNavigation();
   const isNavigating = Boolean(navigation.location);

   return (
      <header className="header">
         <div className="header-inner flex flex-row items-center">
            <Link to="/" className="header-logo">
               <img src="/kiesraad_logo.png" alt="Kiesraad" className="header-logo-img" />
            </Link>
            <FontAwesomeIcon
               icon={faCircleNotch}
               className={twMerge(
                  "text-white animate-spin text-2xl ml-2 opacity-0 transition-opacity duration-300",
                  isNavigating && "opacity-100",
               )}
            />
         </div>
      </header>
   );
}
