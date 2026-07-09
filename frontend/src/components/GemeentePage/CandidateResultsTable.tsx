import type { CandidateResult } from '../../data/pollingStationPartyResults'

type Props = {
  candidates: CandidateResult[]
  totalVotes: number
}

export default function CandidateResultsTable({ candidates, totalVotes }: Props) {
  return (
    <div className="candidate-results-table">
      <div className="candidate-results-table-header">
        <span>Kandidaat</span>
        <span>Aantal stemmen</span>
      </div>
      <div className="candidate-results-table-body">
        {candidates.map((candidate) => (
          <div key={`${candidate.position}-${candidate.name}`} className="candidate-results-table-row">
            <div className="candidate-results-table-name">
              <span className="candidate-results-table-number">{candidate.position}</span>
              <span>{candidate.name}</span>
            </div>
            <span className="candidate-results-table-votes bold">{candidate.votes ?? '-'}</span>
          </div>
        ))}
        <div className="candidate-results-table-row candidate-results-table-total bold">
          <span>Totaal stemmen lijst</span>
          <span>{totalVotes}</span>
        </div>
      </div>
    </div>
  )
}
