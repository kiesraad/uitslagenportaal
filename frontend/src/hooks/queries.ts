import { useQuery } from '@tanstack/react-query'
import { getElectionConfigBySlug, getElectionConfigs, getPartyVoteMatrix, getRegion, getRegions } from '../api/endpoints'
import type { PartyVoteMatrix, Region, RegionCategory } from '../api/types'

export function useElectionConfig(slug: string | undefined) {
  return useQuery({
    queryKey: ['elections', slug],
    queryFn: () => getElectionConfigBySlug(slug!),
    enabled: Boolean(slug),
  })
}

export function useElectionConfigs() {
  return useQuery({
    queryKey: ['election_configs'],
    queryFn: getElectionConfigs,
  })
}

export function useRegion(
  electionConfigSlug: string | undefined,
  regionSlug: string | undefined,
  csbSlug?: string
) {
  return useQuery<Region>({
    queryKey: ['region', electionConfigSlug, regionSlug, csbSlug ?? null],
    queryFn: () => getRegion(electionConfigSlug!, regionSlug!, csbSlug),
    enabled: Boolean(electionConfigSlug) && Boolean(regionSlug),
  })
}

export function useRegions(
  electionConfigSlug: string | undefined,
  parentRegionSlug?: string,
  regionCategory?: RegionCategory,
  skipNode?: boolean,
  csbSlug?: string
) {
  // Validation: Either regionCategory or parentRegionSlug must be present (with electionConfigSlug), but not both undefined.
  const enabled =
    Boolean(electionConfigSlug) &&
    (Boolean(regionCategory) || Boolean(parentRegionSlug));

  return useQuery({
    queryKey: [
      'regions',
      electionConfigSlug,
      parentRegionSlug ?? null,
      regionCategory ?? null,
      skipNode ?? false,
      csbSlug ?? null,
    ],
    queryFn: () => getRegions(electionConfigSlug!, skipNode!, parentRegionSlug, regionCategory, csbSlug),
    enabled,
  });
}

export function usePartyVoteMatrix(
  electionSlug: string | undefined,
  csbSlug: string | undefined,
  partySlug: string | undefined,
) {
  return useQuery<PartyVoteMatrix>({
    queryKey: ['party-vote-matrix', electionSlug, csbSlug, partySlug],
    queryFn: () => getPartyVoteMatrix(electionSlug!, partySlug!, csbSlug!),
    enabled: Boolean(electionSlug) && Boolean(csbSlug) && Boolean(partySlug),
  })
}
