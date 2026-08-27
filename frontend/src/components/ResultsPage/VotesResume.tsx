type Props = {
   votes: VoterTurnoutCount[] | undefined;
};

import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import { Trans, useLingui } from "@lingui/react/macro";
import type { VoterTurnoutCount } from "../../api/types";
import { useFormatters } from "../../utils/format";

// `reason_code` is a key matched literally against the API, not display text —
// it stays in the source language it arrives in. Only `label` is translated.
type VoterTurnoutRow = {
   reason_code: string;
   label: MessageDescriptor;
   bold?: boolean;
   sum_of?: string[];
};

const ADMITTED_VOTER_ROWS: VoterTurnoutRow[] = (() => [
   { reason_code: "geldige stempassen", label: msg`Stempassen` },
   { reason_code: "geldige volmachtbewijzen", label: msg`Volmachtbewijzen` },
   { reason_code: "geldige kiezerspassen", label: msg`Kiezerspassen` },
   { reason_code: "toegelaten kiezers", label: msg`Toegelaten kiezers`, bold: true },
])();

const VOTES_CAST: VoterTurnoutRow[] = (() => [
   { reason_code: "total counted", label: msg`Totaal stemmen op kandidaten`, bold: true },
   { reason_code: "blanco", label: msg`Blanco stemmen` },
   { reason_code: "ongeldig", label: msg`Ongeldige stemmen` },
   {
      reason_code: "cast",
      label: msg`Totaal uitgebrachte stemmen`,
      sum_of: ["total counted", "blanco", "ongeldig"],
   },
])();

function getAdmittedVoterVotes(voterTurnoutCounts: VoterTurnoutCount[] | undefined, rows: VoterTurnoutRow[]) {
   return rows.flatMap(({ reason_code, label, bold, sum_of }) => {
      const count = sum_of
         ? sumVotes(voterTurnoutCounts, sum_of)
         : voterTurnoutCounts?.find((entry) => entry.reason_code === reason_code)?.votes;

      return count === undefined
         ? []
         : [
              {
                 key: reason_code,
                 label,
                 count,
                 ...(bold ? { bold: true as const } : {}),
              },
           ];
   });
}

function sumVotes(voterTurnoutCounts: VoterTurnoutCount[] | undefined, reasonCodes: string[]) {
   const entries = voterTurnoutCounts?.filter((turnoutCount) => reasonCodes.includes(turnoutCount.reason_code));

   return entries ? entries.reduce((total, entry) => total + entry.votes, 0) : undefined;
}

export type VotesResumeType = "admittedVoters" | "votesCast";

export default function VotesResume({ votes, type }: Props & { type: VotesResumeType }) {
   const { t } = useLingui();
   const { formatNumber } = useFormatters();

   const boxVotes = getAdmittedVoterVotes(votes, type === "votesCast" ? VOTES_CAST : ADMITTED_VOTER_ROWS);

   return (
      <section className="admitted-voters">
         {type === "admittedVoters" && (
            <h3 className="mb-2">
               <Trans>Toegelaten kiezers</Trans>
            </h3>
         )}
         <div className={"admitted-voters-box"}>
            {boxVotes.map((vote) => (
               <div key={vote.key} className={`admitted-voters-item ${vote.bold ? "font-semibold" : ""}`}>
                  <span>{t(vote.label)}</span>
                  <span className="font-number">{formatNumber(vote.count)}</span>
               </div>
            ))}
         </div>
      </section>
   );
}
