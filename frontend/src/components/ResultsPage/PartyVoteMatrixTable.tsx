import type { PartyVoteMatrix } from '../../api/types'
import { formatCandidateName } from '../../utils/formatCandidateName'

type Props = {
  matrix: PartyVoteMatrix
}

function formatVotes(value: number | null | undefined): string {
  if (value == null) {
    return '-'
  }

  return value.toLocaleString('nl-NL')
}

function rowTotal(votes: Record<string, number | null>): number {
  return Object.values(votes).reduce<number>((sum, value) => sum + (value ?? 0), 0)
}

export default function PartyVoteMatrixTable({ matrix }: Props) {
  return (
    <div className="party-vote-matrix-scroll">
      <table className="party-vote-matrix">
        <thead>
          <tr>
            <th className="party-vote-matrix-candidate-header">Kandidaat</th>
            <th className="party-vote-matrix-total-header">Totaal</th>
            {matrix.columns.map((column) => (
              <th key={column.slug} className="party-vote-matrix-region-header">
                {column.region_name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.rows.map(({ candidate, votes }) => (
            <tr key={candidate.position}>
              <td className="party-vote-matrix-candidate">
                <span className="party-vote-matrix-position">{candidate.position}</span>
                <span>{formatCandidateName(candidate)}</span>
              </td>
              <td className="party-vote-matrix-total bold">{formatVotes(rowTotal(votes))}</td>
              {matrix.columns.map((column) => (
                <td key={column.slug} className="party-vote-matrix-votes">
                  {formatVotes(votes[column.slug])}
                </td>
              ))}
            </tr>
          ))}
          <tr className="party-vote-matrix-totals-row">
            <td className="party-vote-matrix-candidate">
              <span className="bold">Totaal</span>
            </td>
            <td className="party-vote-matrix-total bold">{formatVotes(matrix.totals.total)}</td>
            {matrix.columns.map((column) => (
              <td key={column.slug} className="party-vote-matrix-votes">
                {formatVotes(matrix.totals.votes[column.slug])}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
