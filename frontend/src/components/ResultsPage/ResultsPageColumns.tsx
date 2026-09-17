import type { ReactNode } from "react";
import ResultsSourceBox from "./ResultsSourceBox";

type Props = {
   children: ReactNode;
};

export default function ResultsPageColumns({ children }: Props) {
   // The proces-verbaal stub is omitted from production builds.
   const showStub = import.meta.env.DEV;

   return (
      <div className={showStub ? "page-main page-main-two-columns" : "page-main"}>
         <div className="page-space-3">{children}</div>
         {showStub && (
            <div className="counting-results-column">
               <ResultsSourceBox />
            </div>
         )}
      </div>
   );
}
