import { Trans, useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import type {
   ElectionDocument,
   TimelineEntry,
   TimelineVariant,
   VoteCount,
   VoteCounts,
   VoterTurnoutCount,
} from "../../api/types";
import { getPartyLevelVoteCounts } from "../../utils/voteCounts";
import IssueNotice from "./IssueNotice";
import ReportsWithResults from "./ReportsWithResults";
import ResultsNotPublished from "./ResultsNotPublished";
import ResultsPageIndex from "./ResultsPageIndex";
import ResultsTimeline from "./ResultsTimeline";
import VotesList, { VotesListItem } from "./VotesList";
import VotesResume from "./VotesResume";

type Props = {
   intro: ReactNode;
   voteCounts: VoteCounts | undefined;
   turnoutVotes: VoterTurnoutCount[] | undefined;
   reports?: {
      description: string;
      documents: ElectionDocument[] | undefined;
   };
   timelineVariant?: TimelineVariant;
   timelineEntries: TimelineEntry[];
   issueReportDeadline: string;
   /** When set, show ResultsNotPublished instead of results when there are no vote counts. */
   notPublishedRegionLabel?: string;
};

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
   const { t } = useLingui();
   const hasResults = Array.isArray(voteCounts) && voteCounts.length > 0;
   const partyLevelVoteCounts = getPartyLevelVoteCounts(voteCounts);
   const showNotPublished = Boolean(notPublishedRegionLabel) && !hasResults;

   const resultsContent = (
      <>
         <ResultsPageIndex />
         <section id="telresultaten">
            <h2 className="mb-2">
               <Trans>Telresultaten</Trans>
            </h2>
            <p>{intro}</p>
         </section>
         <VotesResume type="admittedVoters" votes={turnoutVotes} />
         <section className="votes-cast">
            <h3 className="mb-2">
               <Trans>Uitgebrachte stemmen</Trans>
            </h3>
            <p className="mb-4">
               <Trans>Klik op een lijst om de stemmen per kandidaat te zien</Trans>
            </p>
            <VotesList indexColumn={t`Lijst`}>
               {partyLevelVoteCounts.map((voteCount: VoteCount) => (
                  <VotesListItem
                     key={voteCount.id}
                     number={voteCount.party.list_number}
                     title={voteCount.party.registered_name}
                     voteCount={voteCount.valid_votes}
                     href={`${location.pathname}/${voteCount.party.slug}`}
                  />
               ))}
            </VotesList>
         </section>
         <VotesResume type="votesCast" votes={turnoutVotes} />
         {reports && (
            <ReportsWithResults
               title={t`Brondocumenten`}
               description={reports.description}
               documents={reports.documents}
            />
         )}
      </>
   );

   return (
      <>
         {showNotPublished ? <ResultsNotPublished regionLabel={notPublishedRegionLabel!} /> : resultsContent}
         <ResultsTimeline variant={timelineVariant} entries={timelineEntries} />
         <IssueNotice issueReportDeadline={issueReportDeadline} />
      </>
   );
}
