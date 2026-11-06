import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import { lazy, Suspense, useEffect, useRef } from "react";
import Button from "@/elements/Button.tsx";
import { ExternalLinkIcon } from "@/elements/ExternalLinkIcon.tsx";

// Keeps react-pdf and PDF.js out of the main bundle until a visitor opens the viewer.
const PdfDocument = lazy(() => import("./PdfDocument"));

type Props = {
   documentUrl: string;
   onClose: () => void;
};

export default function PdfViewerPanel({ documentUrl, onClose }: Props) {
   const headingRef = useRef<HTMLHeadingElement>(null);

   // Only mounts when opened, so focus moves into the panel and a screen reader announces it.
   useEffect(() => {
      headingRef.current?.focus();
   }, []);

   return (
      // Sits in a column that sticks 1.5rem from the top; keeps the same space below it.
      <div className="flex max-h-[calc(100dvh-3rem)] flex-col gap-4">
         <div className="flex items-center justify-between gap-4">
            <h2 ref={headingRef} tabIndex={-1} className="h4">
               <Trans>Proces-verbaal</Trans>
            </h2>
            <Button onClick={onClose}>
               <FontAwesomeIcon icon={faXmark} />
               <Trans>Sluiten</Trans>
            </Button>
         </div>
         <Suspense
            fallback={
               <p role="status">
                  <Trans>Proces-verbaal laden…</Trans>
               </p>
            }
         >
            <PdfDocument key={documentUrl} file={documentUrl} />
         </Suspense>
         <p>
            <a href={documentUrl} target="_blank" rel="noopener noreferrer">
               <Trans>Bekijk het proces-verbaal</Trans> <ExternalLinkIcon />
            </a>
         </p>
      </div>
   );
}
