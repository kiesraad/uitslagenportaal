import { createContext, type ReactNode, useCallback, useContext, useState } from "react";
import type { TocEntry } from "@/api/types.ts";
import ResultsSourceBox from "./ResultsSourceBox";

type PvViewerContextProps = {
   documentUrl?: string | null;
   toc?: TocEntry[] | null;
   openViewerAt: (page: number) => void;
};

const PvViewerContext = createContext<PvViewerContextProps>({ openViewerAt: () => {} });

export const usePvViewerContext = () => useContext(PvViewerContext);

type Props = {
   children: ReactNode;
   previewUrl?: string | null;
   documentUrl?: string | null;
   documentToc?: TocEntry[] | null;
   documentMismatch?: boolean;
};

export default function ResultsPageColumns({
   children,
   previewUrl,
   documentUrl,
   documentToc,
   documentMismatch,
}: Props) {
   // The document and page the viewer shows, or null while it is closed.
   const [viewer, setViewer] = useState<{ documentUrl?: string | null; page: number } | null>(null);
   // Another document, as after going to another region, starts at page 1.
   const viewerPage = viewer && (viewer.documentUrl === documentUrl ? viewer.page : 1);
   const setViewerPage = useCallback(
      (page: number | null) => setViewer(page === null ? null : { documentUrl, page }),
      [documentUrl],
   );

   return (
      // The viewer needs the preview as well, so without one there is nothing to link to.
      <PvViewerContext
         value={{ documentUrl: previewUrl && documentUrl, toc: documentToc, openViewerAt: setViewerPage }}
      >
         <div className="page-main page-main-two-columns">
            <div className="flex flex-col gap-4 sm:gap-12">{children}</div>
            <div className="counting-results-column">
               <ResultsSourceBox
                  previewUrl={previewUrl}
                  documentUrl={documentUrl}
                  documentMismatch={documentMismatch}
                  viewerPage={viewerPage}
                  onViewerPageChange={setViewerPage}
               />
            </div>
         </div>
      </PvViewerContext>
   );
}
