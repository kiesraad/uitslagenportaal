import type { VoteCount, VoteCounts } from '../../api/types'

type Props = {
  voteCounts: VoteCounts
  partyVote?: VoteCount
  partyListNumber?: number
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
      <div className="votes-cast-list-header bold" style={{ paddingRight: '3.25rem'}}>
        {columns.map((column, i) => (
          <span key={i}>{column}</span>
        ))}
      </div>
      <div className="votes-cast-list">
        {candidateVotes.map((voteCount, i) => (
          <div key={voteCount.id} className="votes-cast-list-item votes-cast-list-item-static">
            <div className="votes-cast-list-item-child">
              <span>{i + 1}</span>
              <span>{voteCount.candidate?.last_name}, {voteCount.candidate?.first_name}</span>
            </div>
            <div className="votes-cast-list-item-child">
              <span className="votes-cast-list-item-votes bold">{voteCount.valid_votes ? voteCount.valid_votes : '-'}</span>
            </div>
          </div>
        ))}
        {partyVote && (
          <div className="votes-cast-list-item votes-cast-list-item-static">
            <div className="votes-cast-list-item-child">
              <span className="bold">Totaal stemmen lijst {partyListNumber}</span>
            </div>
            <div className="votes-cast-list-item-child">
              <span className="votes-cast-list-item-votes bold">{partyVote.valid_votes ? partyVote.valid_votes : '-'}</span>
            </div>
          </div>
        )}
      </div>
      {total && (
        <div className="votes-cast-list-total bold">
          <span>{total.label}</span>
          <span style={{ marginRight: '2rem'}}>{total.value}</span>
        </div>
      )}
    </div>
  )
}
