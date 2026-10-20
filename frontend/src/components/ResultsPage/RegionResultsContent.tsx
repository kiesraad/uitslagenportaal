import { Trans, useLingui } from "@lingui/react/macro";
import type { ReactNode } from "react";
import type { ElectionDocument, RegionCategory, VoteCount, VoteCounts, VoterTurnoutCount } from "@/api/types.ts";
import { getPartyLevelVoteCounts } from "@/utils/voteCounts.ts";
import IssueNotice from "./IssueNotice";
import ReportsWithResults from "./ReportsWithResults";
import ResultsNotPublished from "./ResultsNotPublished";
import ResultsPageIndex from "./ResultsPageIndex";
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
   timeline?: ReactNode;
   issueReportDeadline: string;
   notPublishedRegionName: string;
   notPublishedRegionCategory: RegionCategory;
   partyHref?: (partySlug: string) => string;
};

export default function RegionResultsContent({
   intro,
   voteCounts,
   turnoutVotes,
   reports,
   timeline,
   issueReportDeadline,
   notPublishedRegionName,
   notPublishedRegionCategory,
   partyHref = (partySlug) => `${location.pathname}/${partySlug}`,
}: Props) {
   const { t } = useLingui();
   const hasResults = Array.isArray(voteCounts) && voteCounts.length > 0;
   const partyLevelVoteCounts = getPartyLevelVoteCounts(voteCounts);

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
                     href={partyHref(voteCount.party.slug)}
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
         {!hasResults ? (
            <ResultsNotPublished regionName={notPublishedRegionName} regionCategory={notPublishedRegionCategory} />
         ) : (
            resultsContent
         )}
         {timeline}
         <IssueNotice issueReportDeadline={issueReportDeadline} />
      </>
   );
}
