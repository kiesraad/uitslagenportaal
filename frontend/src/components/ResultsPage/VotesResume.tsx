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
    return rows.flatMap(({ reason_code, label, bold }) => {
        const voteCount = voterTurnoutCounts?.find((entry) => entry.reason_code === reason_code)

        return voteCount ? [{
            name: label,
            count: voteCount.votes,
            ...(bold ? { bold: true as const } : {}),
        }] : []
    })
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
        <section className="admitted-voters">
            {type === 'admittedVoters' && <h3 className="mb-2">Toegelaten kiezers</h3>}
            <div className={'admitted-voters-box'}>
                {boxVotes.map((vote) => (
                    <div key={vote.name} className={`admitted-voters-item ${vote.bold ? 'font-semibold' : ''}`}>
                        <span>{vote.name}</span>
                        <span>{vote.count.toLocaleString('nl-NL')}</span>
                    </div>
                ))}
            </div>
        </section>
    );
}
