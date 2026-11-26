import { faArrowRight, faMaximize } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { useSuspenseQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { flushSync } from "react-dom";
import { Link, useParams } from "react-router";
import { NewWindowHint } from "@/elements/ExternalLinkIcon.tsx";
import { electionConfigQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import { appRoutes } from "@/utils/routes.ts";
import { InfoBox } from "../InfoBox";
import PdfViewerPanel from "./PdfViewerPanel";
import PvSelect from "./PvSelect";
import type { ViewablePv } from "./ResultsPageColumns";

type Props = {
   pvs: ViewablePv[];
   // The PV shown in the box and the viewer; undefined when the region has none.
   selected?: ViewablePv;
   onSelect: (url: string) => void;
   pvMayDiffer?: boolean;
   // The PV that was open before a link switched to the selected one.
   switchedFromLabel?: string | null;
   // The page the viewer shows, or null while it is closed.
   viewerPage: number | null;
   onViewerPageChange: (page: number | null) => void;
};

export default function ResultsSourceBox({
   pvs,
   selected,
   onSelect,
   pvMayDiffer,
   switchedFromLabel,
   viewerPage,
   onViewerPageChange,
}: Props) {
   const { t } = useLingui();
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(electionConfigSlug));
   const { formatDate } = useFormatters();
   const deadline = formatDate(electionConfig.issue_report_deadline, { delimiter: "at", withYear: false });
   const isViewerOpen = viewerPage !== null;
   const thumbnailRef = useRef<HTMLButtonElement>(null);

   // One column has no room for the viewer; there the thumbnail opens the PDF in a new tab. Matches `lg:`.
   useEffect(() => {
      if (!isViewerOpen) return;
      const wide = window.matchMedia("(min-width: 64rem)");
      const closeWhenNarrow = () => {
         if (!wide.matches) onViewerPageChange(null);
      };
      wide.addEventListener("change", closeWhenNarrow);
      return () => wide.removeEventListener("change", closeWhenNarrow);
   }, [isViewerOpen, onViewerPageChange]);

   function closeViewer() {
      flushSync(() => onViewerPageChange(null));
      thumbnailRef.current?.focus();
   }

   const heading = (
      <h2 className="h4">
         <Trans>Waar komen deze telresultaten vandaan?</Trans>
      </h2>
   );

   if (!selected) {
      return (
         <div className="counting-results-infobox">
            <InfoBox disableMargin>
               {heading}
               <span>
                  <Trans>
                     De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het
                     proces-verbaal dat gemaakt is na het tellen van de stemmen. Momenteel is het proces-verbaal nog
                     niet gepubliceerd en daarom niet zichtbaar.
                  </Trans>
               </span>
            </InfoBox>
         </div>
      );
   }

   const documentUrl = selected.url;
   const pvSelect = <PvSelect pvs={pvs} selected={selected} onSelect={onSelect} />;
   const mayDiffer = pvMayDiffer && (
      <p>
         <Trans>
            Er zijn correcties verwerkt in de telresultaten of in het proces-verbaal. Mogelijk zijn deze nog niet
            allebei bijgewerkt. De aantallen in het proces-verbaal kunnen daardoor afwijken van die op deze pagina.
         </Trans>
      </p>
   );

   if (isViewerOpen) {
      const shownLabel = selected.label;
      return (
         <PdfViewerPanel
            documentUrl={documentUrl}
            pageNumber={viewerPage}
            onPageChange={onViewerPageChange}
            onClose={closeViewer}
            controls={
               <>
                  {pvSelect}
                  {switchedFromLabel && (
                     <p role="status">
                        <Trans>
                           Getoond: {shownLabel}. Dit onderdeel staat niet in {switchedFromLabel}.
                        </Trans>
                     </p>
                  )}
                  {mayDiffer}
               </>
            }
         />
      );
   }

   const thumbnail = (
      <>
         <div className="results-image-resize" aria-hidden="true">
            <FontAwesomeIcon icon={faMaximize} />
         </div>
         <img src={selected.previewUrl} alt={t`Proces-verbaal`} className="results-image" />
      </>
   );

   return (
      <div className="counting-results-infobox">
         <InfoBox disableMargin>
            {heading}
            <span className="mb-2">
               <Trans>
                  De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het
                  proces-verbaal dat gemaakt is na het tellen van de stemmen.
               </Trans>
            </span>
            {mayDiffer && <div className="mb-2">{mayDiffer}</div>}
            {pvs.length > 1 && <div className="mb-2">{pvSelect}</div>}
            {/* Two columns open the viewer beside the counts; one column opens the PDF in a new tab. */}
            <div className="mb-2 lg:hidden">
               <a href={documentUrl} target="_blank" rel="noopener noreferrer" className="results-image-container">
                  {thumbnail}
                  <NewWindowHint />
               </a>
            </div>
            <div className="mb-2 max-lg:hidden">
               <button
                  type="button"
                  ref={thumbnailRef}
                  onClick={() => onViewerPageChange(1)}
                  className="results-image-container w-full cursor-pointer"
               >
                  {thumbnail}
               </button>
            </div>
            <p className="mb-3">
               <a href={documentUrl} target="_blank" rel="noopener noreferrer">
                  <Trans>Bekijk het proces-verbaal</Trans>
                  <FontAwesomeIcon icon={faArrowRight} />
               </a>
            </p>
            <span className="mb-1">
               <Trans>
                  Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de stemmen. Fouten die na{" "}
                  {deadline} worden gemeld, kunnen we nog onderzoeken en herstellen. Dan kan de juiste informatie mee in
                  de officiele uitslag.
               </Trans>
            </span>
            <p>
               <Link to={appRoutes.reportIssue(electionConfigSlug ?? "")}>
                  <Trans>Meld een fout of iets dat niet klopt</Trans>
                  <FontAwesomeIcon icon={faArrowRight} />
               </Link>
            </p>
         </InfoBox>
      </div>
   );
}
