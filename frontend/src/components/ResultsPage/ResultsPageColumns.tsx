import type { ReactNode } from "react";
import ResultsSourceBox from "./ResultsSourceBox";

type Props = {
   children: ReactNode;
   previewUrl?: string | null;
   documentUrl?: string | null;
};

export default function ResultsPageColumns({ children, previewUrl, documentUrl }: Props) {
   return (
      <div className="page-main page-main-two-columns">
         <div className="page-space-3">{children}</div>
         <div className="counting-results-column">
            <ResultsSourceBox previewUrl={previewUrl} documentUrl={documentUrl} />
         </div>
      </div>
   );
}
