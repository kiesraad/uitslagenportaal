import {Link} from 'react-router-dom'
import type {VoteCounts} from '../../api/types'
import {twMerge} from "tailwind-merge";

type Props = {
  voteCounts: VoteCounts
  total?: {
    label: string;
    value: number;
  };
  columns?: string[]
}

export default function VotesList({voteCounts, total, columns = ['Lijst', 'Aantal stemmen']}: Props) {

  return (
    <div className="votes-cast-list-container">

      <div className="grid grid-cols-[max-content_auto_max-content_max-content] gap-x-4">
        <div className="flex justify-between font-semibold pl-4.5 py-3 col-span-3">
          {columns.map((column, i) => (
            <span key={i}>{column}</span>
          ))}
        </div>

        {voteCounts.map((voteCount) => {
          const isClickable = voteCount.valid_votes > 0
          const ListItem = isClickable
            ? ({...props}) => <Link to={`${location.pathname}/${voteCount.party.slug}`} {...props} />
            : ({...props}) => <div {...props} />

          return <ListItem className={twMerge(
            "items-center hover:no-underline! even:bg-blue-50 h-18 px-6 grid col-span-4 grid-cols-subgrid",
            isClickable && "hover:bg-blue-100"
          )}>
            <span className="font-light text-gray-700">{voteCount.party.list_number ?? '-'}</span>
            <span className="in-[a]:text-(--c-blue) in-[a]:underline">{voteCount.party.registered_name}</span>
            <span className="text-right bold">{voteCount.valid_votes.toLocaleString('nl-NL')}</span>
            <span>{isClickable && <span className="gemeente-chevron mb-1">{'>'}</span>}</span>
          </ListItem>
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
