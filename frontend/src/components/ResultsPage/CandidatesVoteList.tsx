import type { VoteCount, VoteCounts } from '../../api/types'
import { formatCandidateName } from '../../utils/formatCandidateName'

type Props = {
  voteCounts: VoteCounts
  partyVote?: VoteCount
  partyListNumber?: number | null
  total?: {
    label: string;
    value: number;
  };
  columns?: string[]
}

export default function CandidatesVoteList({ voteCounts, partyVote, partyListNumber, total, columns = ['Lijst', 'Aantal stemmen'] }: Props) {
  const candidateVotes = voteCounts.filter(voteCount => voteCount.candidate);

  return (
    <div className="votes-cast-list-container">
      <div className="flex justify-between font-semibold pl-4.5 pr-13 py-3">
        {columns.map((column, i) => (
          <span key={i}>{column}</span>
        ))}
      </div>
      <div className="votes-cast-list">
        {candidateVotes.map((voteCount, i) => (
          <div key={voteCount.id} className="votes-cast-list-item votes-cast-list-item-static">
            <div className="votes-cast-list-item-child">
              <span>{i + 1}</span>
              <span>{formatCandidateName(voteCount.candidate!)}</span>
            </div>
            <div className="votes-cast-list-item-child">
              <span className="font-semibold">{voteCount.valid_votes ? voteCount.valid_votes : '-'}</span>
            </div>
          </div>
        ))}
        {partyVote && (
          <div className="votes-cast-list-item votes-cast-list-item-static">
            <div className="votes-cast-list-item-child">
              <span className="font-semibold">Totaal stemmen lijst {partyListNumber ?? '-'}</span>
            </div>
            <div className="votes-cast-list-item-child">
              <span className="font-semibold">{partyVote.valid_votes ? partyVote.valid_votes : '-'}</span>
            </div>
          </div>
        )}
      </div>
      {total && (
        <div className="flex font-semibold items-center justify-between">
          <span>{total.label}</span>
          <span className="mr-8">{total.value}</span>
        </div>
      )}
    </div>
  )
}
