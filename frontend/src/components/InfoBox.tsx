import { faInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { ReactNode } from "react";

interface InfoBoxProps {
   children: ReactNode;
   disableMargin?: boolean;
}

export function InfoBox({ children, disableMargin }: InfoBoxProps) {
   return (
      <div className={`result-info-box ${!disableMargin ? "mt-8 mb-9" : ""}`}>
         <i className="result-info-icon" aria-hidden="true">
            <FontAwesomeIcon icon={faInfo} className="pb-1 text-xs" />
         </i>
         <div className="result-info-body">{children}</div>
      </div>
   );
}
