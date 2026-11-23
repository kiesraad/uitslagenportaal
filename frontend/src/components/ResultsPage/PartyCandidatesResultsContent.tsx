import { Trans, useLingui } from "@lingui/react/macro";
import type { VoteCounts } from "@/api/types.ts";
import VotesList, { VotesListItem } from "@/components/ResultsPage/VotesList.tsx";
import { formatCandidateName } from "@/utils/formatCandidateName.ts";
import { getCandidateVoteCountsForParty, getPartyVoteCount } from "@/utils/voteCounts.ts";
import IssueNotice from "./IssueNotice";
import PvPageLink from "./PvPageLink";
import ResultsPageIndex from "./ResultsPageIndex";

type Props = {
   voteCounts: VoteCounts | undefined;
   partySlug: string;
   issueReportDeadline: string;
};

export default function PartyCandidatesResultsContent({ voteCounts, partySlug, issueReportDeadline }: Props) {
   const { t } = useLingui();
   const partyVoteCount = getPartyVoteCount(voteCounts, partySlug);
   const candidateVoteCounts = getCandidateVoteCountsForParty(voteCounts, partySlug);
   const partyListNumber = partyVoteCount?.party.list_number;
   const partyName = partyVoteCount?.party.registered_name ?? t`Lijst`;
   const listNumber = partyListNumber ?? "-";

   return (
      <>
         <ResultsPageIndex variant="party" />

         <section id="telresultaten">
            <h2 className="mb-4.5">
               <Trans>Telresultaten lijst {listNumber}</Trans>
            </h2>
            <div className="flex flex-wrap items-baseline justify-between gap-x-4">
               <h3 className="party-level-title">{partyName}</h3>
               {partyListNumber != null && <PvPageLink content="candidate-votes" listNumber={partyListNumber} />}
            </div>
            <VotesList
               indexColumn={t`Kandidaat`}
               total={{
                  label: t`Totaal stemmen lijst ${listNumber}`,
                  value: partyVoteCount?.valid_votes ?? 0,
               }}
            >
               {candidateVoteCounts.map((voteCount, i) => (
                  <VotesListItem
                     key={voteCount.id}
                     number={i + 1}
                     title={formatCandidateName(voteCount.candidate)}
                     voteCount={voteCount.valid_votes}
                  />
               ))}
            </VotesList>
         </section>

         <IssueNotice issueReportDeadline={issueReportDeadline} />
      </>
   );
}
