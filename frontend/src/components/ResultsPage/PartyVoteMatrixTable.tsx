import { Trans } from "@lingui/react/macro";
import type { PartyVoteMatrix } from "../../api/types";
import { useFormatters } from "../../utils/format";
import { formatCandidateName } from "../../utils/formatCandidateName";

type Props = {
   matrix: PartyVoteMatrix;
};

export default function PartyVoteMatrixTable({ matrix }: Props) {
   const { formatNumber } = useFormatters();

   function formatVotes(value: number | null | undefined): string {
      if (value == null) {
         return "-";
      }

      return formatNumber(value);
   }

   return (
      <div className="mt-4 max-w-full overflow-x-auto">
         <table className="border-separate border-spacing-0 whitespace-nowrap [&_td]:p-4 [&_th]:p-4">
            <thead>
               <tr className="bg-white text-left align-middle font-bold">
                  <th className="z-20 border-gray-200 border-r border-b bg-inherit sm:sticky sm:left-0">
                     <Trans>Kandidaat</Trans>
                  </th>
                  <th className="min-w-24 border-gray-200 border-b bg-inherit">
                     <Trans>Totaal</Trans>
                  </th>
                  {matrix.columns.map((column) => (
                     <th key={column.slug} className="min-w-24 border-gray-200 border-b bg-inherit">
                        {column.region_name}
                     </th>
                  ))}
               </tr>
            </thead>
            <tbody>
               {matrix.rows.map(({ candidate, total, votes }) => (
                  <tr key={candidate.position} className="bg-white odd:bg-blue-50">
                     <td className="border-gray-200 border-r bg-inherit sm:sticky sm:left-0">
                        <div className="flex items-center sm:gap-3.5">
                           <span className="min-w-6 text-gray-500">{candidate.position}</span>
                           <span>{formatCandidateName(candidate)}</span>
                        </div>
                     </td>
                     <td className="min-w-20 font-bold font-number">{formatVotes(total)}</td>
                     {matrix.columns.map((column) => (
                        <td key={column.slug} className="min-w-16 font-number">
                           {formatVotes(votes[column.slug])}
                        </td>
                     ))}
                  </tr>
               ))}
               <tr className="border-gray-200 border-t bg-white">
                  <td className="border-gray-200 border-t border-r bg-inherit sm:sticky sm:left-0">
                     <div className="flex items-center gap-3.5">
                        <span className="font-bold">
                           <Trans>Totaal</Trans>
                        </span>
                     </div>
                  </td>
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
      </div>
   );
}
