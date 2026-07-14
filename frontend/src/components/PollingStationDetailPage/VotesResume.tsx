type Props = {
    votes: VoterTurnoutCount[] | undefined
}
import type { VoterTurnoutCount } from '../../api/types'

type VoterTurnoutRow = { reason_code: string; label: string; bold?: boolean }


const ADMITTED_VOTER_ROWS: VoterTurnoutRow[] = [
    { reason_code: 'geldige stempassen', label: 'Stempassen' },
    { reason_code: 'geldige volmachtbewijzen', label: 'Volmachtbewijzen' },
    { reason_code: 'geldige kiezerspassen', label: 'Kiezerspassen' },
    { reason_code: 'toegelaten kiezers', label: 'Toegelaten kiezers', bold: true },
  ]

  const VOTES_CAST: VoterTurnoutRow[] = [
    { reason_code: 'total counted', label: 'Totaal stemmen op kandidaten', bold: true },
    { reason_code: 'blanco', label: 'Blanco stemmen' },
    { reason_code: 'ongeldig', label: 'Ongeldige stemmen' },
    { reason_code: 'cast', label: 'Totaal uitgebrachte stemmen' },
  ]


function getAdmittedVoterVotes(voterTurnoutCounts: VoterTurnoutCount[] | undefined, rows: VoterTurnoutRow[]) {
    return rows.map(({ reason_code, label, bold }) => ({
      name: label,
      count: voterTurnoutCounts?.find((entry) => entry.reason_code === reason_code)?.votes ?? 0,
      ...(bold ? { bold: true as const } : {}),
    }))
  }


export type VotesResumeType = 'admittedVoters' | 'votesCast';

export default function VotesResume({ votes, type }: Props & { type: VotesResumeType }) {

    let boxVotes;
    if (type === 'votesCast') {
        boxVotes = getAdmittedVoterVotes(votes, VOTES_CAST);
    } else {
        boxVotes = getAdmittedVoterVotes(votes, ADMITTED_VOTER_ROWS);
    }

    return (
        <div className={'admitted-voters-box'}>
            {boxVotes.map((vote) => (
                <div key={vote.name} className={`admitted-voters-item ${vote.bold ? 'bold' : ''}`}>
                    <span>{vote.name}</span>
                    <span>{vote.count}</span>
                </div>
            ))}
        </div>
    );
}
