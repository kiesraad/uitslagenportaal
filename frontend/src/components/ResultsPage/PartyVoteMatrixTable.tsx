import { Trans } from "@lingui/react/macro";
import { type ReactNode, useId } from "react";
import type { PartyVoteMatrix } from "../../api/types";
import { useFormatters } from "../../utils/format";
import { formatCandidateName } from "../../utils/formatCandidateName";

type Props = {
   matrix: PartyVoteMatrix;
   // Names the table for screen readers; not shown on screen.
   caption: ReactNode;
};

export default function PartyVoteMatrixTable({ matrix, caption }: Props) {
   const { formatNumber } = useFormatters();
   const captionId = useId();

   function formatVotes(value: number | null | undefined): ReactNode {
      // Hidden so screen readers announce an empty cell rather than "streepje".
      if (value == null) {
         return <span aria-hidden="true">-</span>;
      }

      return formatNumber(value);
   }

   return (
      // biome-ignore lint/a11y/noNoninteractiveTabindex: focusable so keyboard users can scroll the table horizontally
      <section aria-labelledby={captionId} tabIndex={0} className="mt-4 max-w-full overflow-x-auto">
         <table className="border-separate border-spacing-0 whitespace-nowrap [&_td]:p-4 [&_th]:p-4">
            <caption id={captionId} className="sr-only">
               {caption}
            </caption>
            <thead>
               <tr className="bg-white text-left align-middle font-bold">
                  <th scope="col" className="z-20 border-gray-200 border-r border-b bg-inherit sm:sticky sm:left-0">
                     <Trans>Kandidaat</Trans>
                  </th>
                  <th scope="col" className="min-w-24 border-gray-200 border-b bg-inherit">
                     <Trans>Totaal</Trans>
                  </th>
                  {matrix.columns.map((column) => (
                     <th key={column.slug} scope="col" className="min-w-24 border-gray-200 border-b bg-inherit">
                        {column.region_name}
                     </th>
                  ))}
               </tr>
            </thead>
            <tbody>
               {matrix.rows.map(({ candidate, total, votes }) => (
                  <tr key={candidate.position} className="bg-white odd:bg-blue-50">
                     <th
                        scope="row"
                        className="border-gray-200 border-r bg-inherit text-left font-normal sm:sticky sm:left-0"
                     >
                        <div className="flex items-center sm:gap-3.5">
                           <span className="min-w-6 text-gray-500">{candidate.position}</span>
                           <span>{formatCandidateName(candidate)}</span>
                        </div>
                     </th>
                     <td className="min-w-20 font-bold font-number">{formatVotes(total)}</td>
                     {matrix.columns.map((column) => (
                        <td key={column.slug} className="min-w-16 font-number">
                           {formatVotes(votes[column.slug])}
                        </td>
                     ))}
                  </tr>
               ))}
               <tr className="border-gray-200 border-t bg-white">
                  <th
                     scope="row"
                     className="border-gray-200 border-t border-r bg-inherit text-left font-normal sm:sticky sm:left-0"
                  >
                     <div className="flex items-center gap-3.5">
                        <span className="font-bold">
                           <Trans>Totaal</Trans>
                        </span>
                     </div>
                  </th>
                  <td className="bold min-w-20 border-gray-200 border-t font-number">
                     {formatVotes(matrix.totals.total)}
                  </td>
                  {matrix.columns.map((column) => (
                     <td key={column.slug} className="min-w-16 border-gray-200 border-t font-number">
                        {formatVotes(matrix.totals.votes[column.slug])}
                     </td>
                  ))}
               </tr>
            </tbody>
         </table>
      </section>
   );
}
