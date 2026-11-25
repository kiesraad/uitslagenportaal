import { faBookmark } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import type { TocEntry } from "@/api/types.ts";
import { NewWindowHint } from "@/elements/ExternalLinkIcon.tsx";
import { usePvViewerContext } from "./ResultsPageColumns";

type Props = {
   content: TocEntry["content"];
   // Narrows the pages to those of one list.
   listNumber?: number;
};

/** Links to the first page that holds `content`, in the selected PV when it has one, else in the first PV that
 * does; renders nothing while no PV has that page. So the links stay put when another PV is chosen. */
export default function PvPageLink({ content, listNumber }: Props) {
   const { findTarget, openViewerAt } = usePvViewerContext();
   const target = findTarget(content, listNumber);
   if (!target) return null;

   const label = (
      <>
         <FontAwesomeIcon icon={faBookmark} /> <Trans>Toon in proces-verbaal</Trans>
      </>
   );

   return (
      <>
         {/* One column has no room for the viewer; there the PDF opens at the page in a new tab. */}
         <a
            href={`${target.pv.url}#page=${target.page}`}
            target="_blank"
            rel="noopener noreferrer"
            className="lg:hidden"
         >
            {label}
            <NewWindowHint />
         </a>
         <button
            type="button"
            onClick={() => openViewerAt(target)}
            className="cursor-pointer text-blue-500 hover:underline max-lg:hidden"
         >
            {label}
         </button>
      </>
   );
}
