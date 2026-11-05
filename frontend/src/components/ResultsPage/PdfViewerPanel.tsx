import { faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import { useEffect, useRef } from "react";
import Button from "@/elements/Button.tsx";

type Props = {
   onClose: () => void;
};

export default function PdfViewerPanel({ onClose }: Props) {
   const headingRef = useRef<HTMLHeadingElement>(null);

   // Only mounts when opened, so focus moves into the panel and a screen reader announces it.
   useEffect(() => {
      headingRef.current?.focus();
   }, []);

   return (
      <div className="flex flex-col gap-4">
         <div className="flex items-center justify-between gap-4">
            <h2 ref={headingRef} tabIndex={-1} className="h4">
               <Trans>Proces-verbaal</Trans>
            </h2>
            <Button onClick={onClose}>
               <FontAwesomeIcon icon={faXmark} />
               <Trans>Sluiten</Trans>
            </Button>
         </div>
      </div>
   );
}
