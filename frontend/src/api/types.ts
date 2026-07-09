export type ElectionConfig = {
  slug: string
  label: string
  date: string
  steps?: ElectionStep[]
}

export type ElectionConfigsResponse = ElectionConfig[]

export type ElectionStepState = 'pending' | 'in-progress' | 'done'

export type ElectionStep = {
  position: number
  state: ElectionStepState
  title: string
  date: string
  body: string
}

export type RegionCategory = 'STAAT' | 'WATERSCHAP' | 'KIESKRING' | 'GEMEENTE' | 'PROVINCIE' | "STEMBUREAU"

export type Region = {
  region_name: string
  slug: string
  vote_counts: VoteCounts
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