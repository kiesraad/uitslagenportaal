import { useLingui } from "@lingui/react/macro";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Must be set in the module that renders react-pdf, or its default can overwrite it.
pdfjs.GlobalWorkerOptions.workerSrc = new URL("pdfjs-dist/build/pdf.worker.min.mjs", import.meta.url).toString();

type Props = {
   file: string;
};

export default function PdfDocument({ file }: Props) {
   const { t } = useLingui();
   const containerRef = useRef<HTMLDivElement>(null);
   const [width, setWidth] = useState<number>();

   useEffect(() => {
      setWidth(containerRef.current?.clientWidth);
   }, []);

   const loading = <p role="status">{t`Proces-verbaal laden…`}</p>;
   const error = <p role="alert">{t`Het proces-verbaal kon niet worden geladen.`}</p>;

   return (
      <div ref={containerRef}>
         {width !== undefined && (
            <Document file={file} suspense={false} loading={loading} error={error}>
               <Page pageNumber={1} width={width} loading={loading} error={error} />
            </Document>
         )}
      </div>
   );
}
