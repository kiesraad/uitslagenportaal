import type { ReactNode } from 'react'
import type {
  ElectionDocument,
  TimelineEntry,
  TimelineVariant,
  VoteCounts,
  VoterTurnoutCount,
} from '../../api/types'
import ResultsPageIndex from './ResultsPageIndex'
import VotesResume from './VotesResume'
import VotesList from './VotesList'
import ReportsWithResults from './ReportsWithResults'
import ResultsNotPublished from './ResultsNotPublished'
import ResultsTimeline from './ResultsTimeline'
import IssueNotice from './IssueNotice'
import { getPartyLevelVoteCounts } from '../../utils/voteCounts'

type Props = {
  intro: ReactNode
  voteCounts: VoteCounts | undefined
  turnoutVotes: VoterTurnoutCount[] | undefined
  reports?: {
    description: string
    documents: ElectionDocument[] | undefined
  }
  timelineVariant?: TimelineVariant
  timelineEntries: TimelineEntry[]
  issueReportDeadline: string
  /** When set, show ResultsNotPublished instead of results when there are no vote counts. */
  notPublishedRegionLabel?: string
}

export default function RegionResultsContent({
  intro,
  voteCounts,
  turnoutVotes,
  reports,
  timelineVariant,
  timelineEntries,
  issueReportDeadline,
  notPublishedRegionLabel,
}: Props) {
  const hasResults = Array.isArray(voteCounts) && voteCounts.length > 0
  const partyLevelVoteCounts = getPartyLevelVoteCounts(voteCounts)
  const showNotPublished = Boolean(notPublishedRegionLabel) && !hasResults

  const resultsContent = (
    <>
      <ResultsPageIndex />
      <section id="telresultaten">
        <h2 className="mb-2">Telresultaten</h2>
        <p>{intro}</p>
      </section>
      <VotesResume type="admittedVoters" votes={turnoutVotes} />
      <section className="votes-cast">
        <h3 className="mb-2">Uitgebrachte stemmen</h3>
        <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
        <VotesList voteCounts={partyLevelVoteCounts} />
      </section>
      <VotesResume type="votesCast" votes={turnoutVotes} />
      {reports && (
        <ReportsWithResults
          title="Brondocumenten"
          description={reports.description}
          documents={reports.documents}
        />
      )}
    </>
  )

  return (
    <>
      {showNotPublished ? (
        <ResultsNotPublished regionLabel={notPublishedRegionLabel!} />
      ) : (
        resultsContent
      )}
      <ResultsTimeline variant={timelineVariant} entries={timelineEntries} />
      <IssueNotice issueReportDeadline={issueReportDeadline} />
    </>
  )
}
