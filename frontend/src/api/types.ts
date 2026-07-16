export type ElectionConfig = {
  slug: string
  label: string
  date: string
  csb_type: RegionCategory
  timeline_entries?: TimelineEntry[]
}

export type ElectionConfigsResponse = ElectionConfig[]

export type TimelineEntryStatus = 'pending' | 'in-progress' | 'done'

export type TimelineEntry = {
  status: TimelineEntryStatus
  title: string
  date: string
  body: string
}

export type ElectionDocument = {
  name: string
  url: string
  type: string
  size: string
  description: string
  file_type: string
}

export type RegionCategory = 'STAAT' | 'WATERSCHAP' | 'KIESKRING' | 'GEMEENTE' | 'PROVINCIE' | "STEMBUREAU"

export type VoterTurnoutCategory = 'REJECTED' | 'UNCOUNTED'

export type VoterTurnoutCount = {
  cast: number
  total_counted: number
  category: VoterTurnoutCategory
  reason_code: string
  votes: number
}

export type Region = {
  region_name: string
  slug: string
  vote_counts: VoteCounts
  voter_turnout_counts?: VoterTurnoutCount[]
  timeline_entries?: TimelineEntry[]
  documents?: ElectionDocument[]
}

export type RegionResponse = Region[]

export type Party = {
  registered_name: string
  slug: string
}

export type Candidate = {
  position: number
  initials: string
  first_name: string | null
  name_prefix: string | null
  last_name: string
}

export type VoteResultLevel = "PARTY" | "CANDIDATE"

export type VoteCount = {
  valid_votes: number
  id: number
  candidate: Candidate | null
  party: Party
  result_level: VoteResultLevel
}

export type VoteCounts = VoteCount[]