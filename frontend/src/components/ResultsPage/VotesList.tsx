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
      <div className="flex justify-between font-semibold pl-4.5 pr-13 py-3">
        {columns.map((column, i) => (
          <span key={i}>{column}</span>
        ))}
      </div>
      <div className="votes-cast-list">
        {voteCounts.map((voteCount, i) => {
          const isClickable = voteCount.valid_votes > 0

          const content = (
            <>
              <div className="flex items-center gap-3">
                <span>{i + 1}</span>
                <span className="in-[a]:text-(--c-blue) in-[a]:underline">{voteCount.party.registered_name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="votes-cast-list-item-votes bold">{voteCount.valid_votes.toLocaleString('nl-NL')}</span>
                {isClickable && <span className="gemeente-chevron mb-1">{'>'}</span>}
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
        <div className="font-semibold flex items-center justify-between p-4.5">
          <span>{total.label}</span>
          <span className="mr-8">{total.value}</span>
        </div>
      )}
    </div>
  )
}
