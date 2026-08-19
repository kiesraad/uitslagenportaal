import type { VoteCounts } from "@/api/types.ts";
import VotesList, { VotesListItem } from "@/components/ResultsPage/VotesList.tsx";
import { formatCandidateName } from "@/utils/formatCandidateName.ts";
import { getCandidateVoteCountsForParty, getPartyVoteCount } from "@/utils/voteCounts.ts";
import IssueNotice from "./IssueNotice";
import ResultsPageIndex from "./ResultsPageIndex";

type Props = {
   voteCounts: VoteCounts | undefined;
   partySlug: string;
   issueReportDeadline: string;
};

export default function PartyCandidatesResultsContent({ voteCounts, partySlug, issueReportDeadline }: Props) {
   const partyVoteCount = getPartyVoteCount(voteCounts, partySlug);
   const candidateVoteCounts = getCandidateVoteCountsForParty(voteCounts, partySlug);
   const partyListNumber = partyVoteCount?.party.list_number;
   const partyName = partyVoteCount?.party.registered_name ?? "Lijst";

   return (
      <>
         <ResultsPageIndex variant="party" />

         <section id="telresultaten">
            <h2 className="mb-4.5">Telresultaten lijst {partyListNumber ?? "-"}</h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>
            <VotesList
               indexColumn="Kandidaat"
               total={{
                  label: `Totaal stemmen lijst ${partyListNumber ?? "-"}`,
                  value: partyVoteCount?.valid_votes ?? 0,
               }}
            >
               {candidateVoteCounts.map((voteCount, i) => (
                  <VotesListItem
                     key={voteCount.id}
                     number={i + 1}
                     title={formatCandidateName(voteCount.candidate!)}
                     voteCount={voteCount.valid_votes}
                  />
               ))}
            </VotesList>
         </section>

         <IssueNotice issueReportDeadline={issueReportDeadline} />
      </>
   );
}
