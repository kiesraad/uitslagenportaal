import { Link } from 'react-router-dom'
import type { VoteCounts } from '../../api/types'

type Props = {
  voteCounts: VoteCounts
  total?: {
    label: string;
    value: number;
  };
  columns?: string[]
}

export default function VotesList({ voteCounts, total, columns = ['Lijst', 'Aantal stemmen'] }: Props) {

  return (
    <div className="votes-cast-list-container">
      <div className="votes-cast-list-header bold" style={{ paddingRight: '3.25rem' }}>
        {columns.map((column, i) => (
          <span key={i}>{column}</span>
        ))}
      </div>
      <div className="votes-cast-list">
        {voteCounts.map((voteCount, i) => {
          const isClickable = voteCount.valid_votes > 0

          const content = (
            <>
              <div className="votes-cast-list-item-child">
                <span>{i + 1}</span>
                <span className={isClickable ? 'votes-cast-list-item-link' : undefined}>{voteCount.party.registered_name}</span>
              </div>
              <div className="votes-cast-list-item-child">
                <span className="votes-cast-list-item-votes bold">{voteCount.valid_votes}</span>
                {isClickable && <span className="gemeente-chevron">{'>'}</span>}
              </div>
            </>
          )

          if (!isClickable) {
            return (
              <div key={voteCount.id} className="votes-cast-list-item votes-cast-list-item-static">
                {content}
              </div>
            )
          }

          return (
            <Link key={voteCount.party.registered_name}
              to={`${location.pathname}/${voteCount.party.slug}`}
              className="votes-cast-list-item">
              {content}
            </Link>
          )
        })}
      </div>
      {total && (
        <div className="votes-cast-list-total bold">
          <span>{total.label}</span>
          <span style={{ marginRight: '2rem' }}>{total.value}</span>
        </div>
      )}
    </div>
  )
}
