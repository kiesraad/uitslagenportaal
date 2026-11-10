import { faChevronLeft, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import Button from "@/elements/Button.tsx";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Must be set in the module that renders react-pdf, or its default can overwrite it.
pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

// Copied there by vite.config.ts. A constant, because react-pdf reloads the PDF when its options change.
const options = { wasmUrl: `${import.meta.env.BASE_URL}pdfjs-wasm/` };

type Props = {
   file: string;
};

export default function PdfDocument({ file }: Props) {
   const { t } = useLingui();
   const containerRef = useRef<HTMLElement>(null);
   const previousRef = useRef<HTMLButtonElement>(null);
   const nextRef = useRef<HTMLButtonElement>(null);
   const [width, setWidth] = useState<number>();
   const [numPages, setNumPages] = useState<number>();
   const [pageNumber, setPageNumber] = useState(1);

   useEffect(() => {
      const container = containerRef.current;
      if (!container) return;
      setWidth(container.clientWidth);
      const observer = new ResizeObserver(() => setWidth(container.clientWidth));
      observer.observe(container);
      return () => observer.disconnect();
   }, []);

   function goToPage(page: number) {
      setPageNumber(page);
      // The button that was pressed becomes disabled at either end, so focus moves to the other one.
      if (page === 1) nextRef.current?.focus();
      if (page === numPages) previousRef.current?.focus();
      if (containerRef.current) {
         containerRef.current.scrollTop = 0;
      }
   }

   const loading = <p role="status">{t`Proces-verbaal laden…`}</p>;
   const error = <p role="alert">{t`Het proces-verbaal kon niet worden geladen.`}</p>;

   return (
      <>
         <div className="flex items-center justify-between gap-4">
            <Button
               ref={previousRef}
               aria-label={t`Vorige pagina`}
               disabled={pageNumber === 1}
               onClick={() => goToPage(pageNumber - 1)}
            >
               <FontAwesomeIcon icon={faChevronLeft} />
            </Button>
            {/* Rendered always, so screen readers pick up changes to its text. */}
            <p role="status">
               {numPages !== undefined && (
                  <Trans>
                     Pagina {pageNumber} van {numPages}
                  </Trans>
               )}
            </p>
            <Button
               ref={nextRef}
               aria-label={t`Volgende pagina`}
               disabled={pageNumber === (numPages ?? 1)}
               onClick={() => goToPage(pageNumber + 1)}
            >
               <FontAwesomeIcon icon={faChevronRight} />
            </Button>
         </div>
         {/* The stable gutter keeps the measured width correct once the scrollbar appears. */}
         <section
            ref={containerRef}
            aria-label={t`Proces-verbaal`}
            // biome-ignore lint/a11y/noNoninteractiveTabindex: focusable so keyboard users can scroll the page
            tabIndex={0}
            className="[scrollbar-gutter:stable] overflow-y-auto"
         >
            {width !== undefined && (
               <Document
                  file={file}
                  options={options}
                  suspense={false}
                  loading={loading}
                  error={error}
                  onLoadSuccess={(pdf) => setNumPages(pdf.numPages)}
               >
                  {/* No loading text on a page change: it would flash, and the indicator already announces it. */}
                  <Page pageNumber={pageNumber} width={width} loading={null} error={error} />
               </Document>
            )}
         </section>
      </>
   );
}
