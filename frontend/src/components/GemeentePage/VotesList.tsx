import { Link } from 'react-router-dom'

type Props = {
  votes: Array<{ name: string; votes: number; url?: string }>
  total?: {
    label: string;
    value: number;
  };
  columns?: string[]
}

export default function VotesList({ votes, total, columns = ['Lijst', 'Aantal stemmen'] }: Props) {

  return (
    <div className="votes-cast-list-container">
      <div className="votes-cast-list-header bold" style={{ paddingRight: votes[0]?.url ? '3.25rem' : '1.15rem' }}>
        {columns.map((column, i) => (
          <span key={i}>{column}</span>
        ))}
      </div>
      <div className="votes-cast-list">
        {votes.map((vote, i) => {
          const content = (
            <>
              <div className="votes-cast-list-item-child">
                <span>{i + 1}</span>
                <span className={vote.url ? "votes-cast-list-item-link" : ""}>{vote.name}</span>
              </div>
              <div className="votes-cast-list-item-child">
                <span className="votes-cast-list-item-votes bold">{(vote.votes || '-')}</span>
                {vote.url && <span className="gemeente-chevron">{'>'}</span>}
              </div>
            </>
          )

          if (!vote.url) {
            return (
              <div key={vote.name} className="votes-cast-list-item votes-cast-list-item-static">
                {content}
              </div>
            )
          }

          return (
            <Link key={vote.name} to={vote.url} className="votes-cast-list-item">
              {content}
            </Link>
          )
        })}
      </div>
      {total && (
        <div className="votes-cast-list-total bold">
          <span>{total.label}</span>
          <span style={{ marginRight: votes[0]?.url ? '2rem' : '' }}>{total.value}</span>
        </div>
      )}
    </div>
  )
}
