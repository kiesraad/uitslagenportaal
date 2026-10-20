import { faInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import type { ReactNode } from "react";
import { twMerge } from "tailwind-merge";

interface InfoBoxProps {
   children: ReactNode;
   disableMargin?: boolean;
   className?: string;
}

export function InfoBox({ children, disableMargin, className }: InfoBoxProps) {
   return (
      <div className={twMerge("result-info-box", !disableMargin && "mt-8 mb-9", className)}>
         <i className="result-info-icon" aria-hidden="true">
            <FontAwesomeIcon icon={faInfo} className="pb-1 text-xs" />
         </i>
         <div className="result-info-body">{children}</div>
      </div>
   );
}
