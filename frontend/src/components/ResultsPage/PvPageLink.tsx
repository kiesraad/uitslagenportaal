import { faBookmark } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import type { TocEntry } from "@/api/types.ts";
import { NewWindowHint } from "@/elements/ExternalLinkIcon.tsx";
import { usePvViewerContext } from "./ResultsPageColumns";

type Props = {
   content: TocEntry["content"];
};

/** Links to the first page of the proces-verbaal that holds `content`; renders nothing while that page is unknown. */
export default function PvPageLink({ content }: Props) {
   const { documentUrl, toc, openViewerAt } = usePvViewerContext();
   const page = toc?.find((entry) => entry.content === content)?.page;
   if (!documentUrl || page === undefined) return null;

   const label = (
      <>
         <FontAwesomeIcon icon={faBookmark} /> <Trans>Toon in proces-verbaal</Trans>
      </>
   );

   return (
      <>
         {/* One column has no room for the viewer; there the PDF opens at the page in a new tab. */}
         <a href={`${documentUrl}#page=${page}`} target="_blank" rel="noopener noreferrer" className="lg:hidden">
            {label}
            <NewWindowHint />
         </a>
         <button
            type="button"
            onClick={() => openViewerAt(page)}
            className="cursor-pointer text-blue-500 hover:underline max-lg:hidden"
         >
            {label}
         </button>
      </>
   );
}
