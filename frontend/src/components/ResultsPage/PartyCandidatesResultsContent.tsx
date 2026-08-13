import type { VoteCounts } from '../../api/types'
import ResultsPageIndex from './ResultsPageIndex'
import CandidatesVoteList from './CandidatesVoteList'
import IssueNotice from './IssueNotice'
import { getCandidateVoteCountsForParty, getPartyVoteCount } from '../../utils/voteCounts'

type Props = {
  voteCounts: VoteCounts | undefined
  partySlug: string
  issueReportDeadline: string
}

export default function PartyCandidatesResultsContent({
  voteCounts,
  partySlug,
  issueReportDeadline,
}: Props) {
  const partyVoteCount = getPartyVoteCount(voteCounts, partySlug)
  const candidateVoteCounts = getCandidateVoteCountsForParty(voteCounts, partySlug)
  const partyListNumber = partyVoteCount?.party.list_number
  const partyName = partyVoteCount?.party.registered_name ?? 'Lijst'

  return (
    <>
      <ResultsPageIndex variant="party" />

      <section id="telresultaten">
        <h2 className="mb-4.5">Telresultaten lijst {partyListNumber ?? '-'}</h2>
        <h3 className="party-level-title mb-2">{partyName}</h3>
        <CandidatesVoteList
          voteCounts={candidateVoteCounts}
          partyVote={partyVoteCount}
          partyListNumber={partyListNumber}
        />
      </section>

      <IssueNotice issueReportDeadline={issueReportDeadline} />
    </>
  )
}
