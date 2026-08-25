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
      <div className="party-vote-matrix-scroll">
         <table className="party-vote-matrix">
            <thead>
               <tr>
                  <th className="party-vote-matrix-candidate-header">
                     <Trans>Kandidaat</Trans>
                  </th>
                  <th>
                     <Trans>Totaal</Trans>
                  </th>
                  {matrix.columns.map((column) => (
                     <th key={column.slug} className="party-vote-matrix-region-header">
                        {column.region_name}
                     </th>
                  ))}
               </tr>
            </thead>
            <tbody>
               {matrix.rows.map(({ candidate, total, votes }) => (
                  <tr key={candidate.position}>
                     <td className="party-vote-matrix-candidate">
                        <span className="party-vote-matrix-position">{candidate.position}</span>
                        <span>{formatCandidateName(candidate)}</span>
                     </td>
                     <td className="party-vote-matrix-total font-bold font-number">{formatVotes(total)}</td>
                     {matrix.columns.map((column) => (
                        <td key={column.slug} className="party-vote-matrix-votes font-number">
                           {formatVotes(votes[column.slug])}
                        </td>
                     ))}
                  </tr>
               ))}
               <tr className="party-vote-matrix-totals-row">
                  <td className="party-vote-matrix-candidate">
                     <span className="font-bold">
                        <Trans>Totaal</Trans>
                     </span>
                  </td>
                  <td className="party-vote-matrix-total bold font-number">{formatVotes(matrix.totals.total)}</td>
                  {matrix.columns.map((column) => (
                     <td key={column.slug} className="party-vote-matrix-votes font-number">
                        {formatVotes(matrix.totals.votes[column.slug])}
                     </td>
                  ))}
               </tr>
            </tbody>
         </table>
      </div>
   );
}
