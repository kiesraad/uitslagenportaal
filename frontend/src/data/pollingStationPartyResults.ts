import POLLING_STATION_VOTES from '../assets/votes_cast_polling_station.json'
import MUNICIPALITY_VOTES from '../assets/votes_cast_municipality.json'

export type CandidateResult = {
  position: number
  name: string
  votes: number | null
}

export type PartyLevelResult = {
  listNumber: number
  partyName: string
  totalVotes: number
  candidates: CandidateResult[]
}

const FALLBACK_CANDIDATE_NAMES = [
  'Kandidaat 1',
  'Kandidaat 2',
  'Kandidaat 3',
  'Kandidaat 4',
  'Kandidaat 5',
  'Kandidaat 6',
  'Kandidaat 7',
  'Kandidaat 8',
  'Kandidaat 9',
  'Kandidaat 10',
  'Kandidaat 11',
  'Kandidaat 12',
  'Kandidaat 13',
  'Kandidaat 14',
  'Kandidaat 15',
  'Kandidaat 16',
  'Kandidaat 17',
  'Kandidaat 18',
  'Kandidaat 19',
  'Kandidaat 20',
  'Kandidaat 21',
  'Kandidaat 22',
  'Kandidaat 23',
  'Kandidaat 24',
  'Kandidaat 25',
  'Kandidaat 26',
  'Kandidaat 27',
  'Kandidaat 28',
  'Kandidaat 29',
]

const EEUWENOUDE_AARDE_UNIE_CANDIDATES: CandidateResult[] = [
  { position: 1, name: 'Zilverlicht, E. (Eldor)', votes: 15 },
  { position: 2, name: 'Donderbrul, G. (Grom)', votes: 9 },
  { position: 3, name: 'Fluisterwind, S. (Seraphina)', votes: null },
  { position: 4, name: 'Nachtschaduw, V. (Vesper)', votes: null },
  { position: 5, name: 'Stormvleugel, R. (Ravian)', votes: null },
  { position: 6, name: 'Sterrenzwever, M. (Mirela)', votes: 7 },
  { position: 7, name: 'Maanfluisteraar, X. (Xander)', votes: null },
  { position: 8, name: 'Windzanger, P. (Phaeton)', votes: null },
  { position: 9, name: 'Vuurvlinder, F. (Faeia)', votes: null },
  { position: 10, name: 'Rotsbreker, H. (Helga)', votes: null },
  { position: 11, name: 'Zonnewende, L. (Luna)', votes: null },
  { position: 12, name: 'Groenhart, T. (Timo)', votes: null },
  { position: 13, name: 'Veldbloem, N. (Naima)', votes: null },
  { position: 14, name: 'Liveren, V. (Vincent)', votes: 2 },
  { position: 15, name: 'Blauwhoof, P. (Priya)', votes: 1 },
  { position: 16, name: 'Windmaker, J. (Jamal)', votes: 1 },
  { position: 17, name: 'Sterrenveld, E. (Esmee)', votes: null },
  { position: 18, name: 'Roodman, M. (Mohammed)', votes: null },
  { position: 19, name: 'Zilverberg, C. (Chen)', votes: null },
  { position: 20, name: 'Duinwalker, S. (Soraya)', votes: 2 },
  { position: 21, name: 'Lichtveld, A. (Alex)', votes: null },
  { position: 22, name: 'Kruidentuin, H. (Habiba)', votes: null },
  { position: 23, name: 'Vlietstra, B. (Bram)', votes: null },
  { position: 24, name: 'Meermin, K. (Kai)', votes: 1 },
  { position: 25, name: 'Goudappel, D. (Diana)', votes: null },
  { position: 26, name: 'Bosrank, F. (Finn)', votes: null },
  { position: 27, name: 'Sterrenveld, J. (Julia)', votes: null },
  { position: 28, name: 'Regenboog, G. (Giovanni)', votes: null },
  { position: 29, name: 'Hemelrijk, M. (Milan)', votes: null },
]

type PartyVote = {
  name: string
  votes: number
}

function buildFallbackCandidates(totalVotes: number) {
  const rows = FALLBACK_CANDIDATE_NAMES.map((name, index) => ({
    position: index + 1,
    name,
    votes: null as number | null,
  }))

  if (totalVotes <= 0) {
    return rows
  }

  const buckets = [0.42, 0.27, 0.16, 0.09, 0.06]
  const allocatedVotes = buckets.map((weight) => Math.floor(totalVotes * weight))
  let remainder = totalVotes - allocatedVotes.reduce((sum, value) => sum + value, 0)

  for (let index = 0; index < allocatedVotes.length; index += 1) {
    rows[index].votes = allocatedVotes[index]
  }

  let cursor = 0
  while (remainder > 0) {
    rows[cursor].votes = (rows[cursor].votes ?? 0) + 1
    remainder -= 1
    cursor = (cursor + 1) % allocatedVotes.length
  }

  return rows
}

function scaleCandidateVotes(candidates: CandidateResult[], totalVotes: number) {
  const knownVotes = candidates.reduce((sum, candidate) => sum + (candidate.votes ?? 0), 0)

  if (knownVotes === 0 || knownVotes === totalVotes) {
    return candidates
  }

  const scaledCandidates = candidates.map((candidate) => ({
    ...candidate,
    votes: candidate.votes === null ? null : Math.floor((candidate.votes / knownVotes) * totalVotes),
  }))
  let remainder = totalVotes - scaledCandidates.reduce((sum, candidate) => sum + (candidate.votes ?? 0), 0)
  let cursor = 0

  while (remainder > 0 && scaledCandidates.length > 0) {
    const candidate = scaledCandidates[cursor]

    if (candidate.votes !== null) {
      candidate.votes += 1
      remainder -= 1
    }

    cursor = (cursor + 1) % scaledCandidates.length
  }

  return scaledCandidates
}

function buildPartyResults(votes: PartyVote[]) {
  return votes.map((vote, index) => {
    const cleanPartyName = vote.name

    if (cleanPartyName === 'Eeuwenoude Aarde Unie') {
      return {
        listNumber: index + 1,
        partyName: cleanPartyName,
        totalVotes: vote.votes,
        candidates: scaleCandidateVotes(EEUWENOUDE_AARDE_UNIE_CANDIDATES, vote.votes),
      }
    }

    return {
      listNumber: index + 1,
      partyName: cleanPartyName,
      totalVotes: vote.votes,
      candidates: buildFallbackCandidates(vote.votes),
    }
  })
}

export const POLLING_STATION_PARTY_RESULTS: PartyLevelResult[] = buildPartyResults(POLLING_STATION_VOTES)
export const MUNICIPALITY_PARTY_RESULTS: PartyLevelResult[] = buildPartyResults(MUNICIPALITY_VOTES)

export function getPartyLevelResult(partyName: string, scope: 'municipality' | 'polling-station' = 'polling-station') {
  const results = scope === 'municipality' ? MUNICIPALITY_PARTY_RESULTS : POLLING_STATION_PARTY_RESULTS

  return results.find((party) => party.partyName === partyName) ?? null
}
