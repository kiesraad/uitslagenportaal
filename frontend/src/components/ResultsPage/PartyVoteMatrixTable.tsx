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
      <div className="max-w-full min-w-0 mt-4 overflow-x-auto">
         <table className="party-vote-matrix max-w-max min-w-full border-collapse whitespace-nowrap [&_td]:p-4 [&_th]:p-4">
            <thead>
               <tr className="font-bold border-b border-gray-200 bg-white text-left align-middle">
                  <th className="flex border-r border-gray-200 sticky left-0 top-0 bg-inherit">
                     <Trans>Kandidaat</Trans>
                  </th>
                  <th>
                     <Trans>Totaal</Trans>
                  </th>
                  {matrix.columns.map((column) => (
                     <th key={column.slug} className="min-w-24">
                        {column.region_name}
                     </th>
                  ))}
               </tr>
            </thead>
            <tbody>
               {matrix.rows.map(({ candidate, total, votes }) => (
                  <tr key={candidate.position} className="bg-white odd:bg-blue-50">
                     <td className="flex items-center gap-3.5 border-r border-gray-200 bg-inherit sticky left-0">
                        <span className="min-w-6 text-gray-500">{candidate.position}</span>
                        <span>{formatCandidateName(candidate)}</span>
                     </td>
                     <td className="min-w-20 font-bold font-number">{formatVotes(total)}</td>
                     {matrix.columns.map((column) => (
                        <td key={column.slug} className="min-w-16 font-number">
                           {formatVotes(votes[column.slug])}
                        </td>
                     ))}
                  </tr>
               ))}
               <tr className="border-t border-gray-200 bg-white">
                  <td className="flex items-center gap-3.5 border-r border-gray-200 bg-inherit sticky left-0">
                     <span className="font-bold">
                        <Trans>Totaal</Trans>
                     </span>
                  </td>
                  <td className="min-w-20 bold font-number">{formatVotes(matrix.totals.total)}</td>
                  {matrix.columns.map((column) => (
                     <td key={column.slug} className="min-w-16 font-number">
                        {formatVotes(matrix.totals.votes[column.slug])}
                     </td>
                  ))}
               </tr>
            </tbody>
         </table>
      </div>
   );
}
