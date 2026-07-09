import { useQuery } from '@tanstack/react-query'
import { getElectionConfigBySlug, getElectionConfigs, getRegion, getRegions } from '../api/endpoints'
import type { Region, RegionCategory } from '../api/types'

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
  regionSlug: string | undefined
) {
  return useQuery<Region>({
    queryKey: ['region', electionConfigSlug, regionSlug],
    queryFn: () => getRegion(electionConfigSlug!, regionSlug!),
    enabled: Boolean(electionConfigSlug) && Boolean(regionSlug),
  })
}

export function useRegions(
  electionConfigSlug: string | undefined,
  parentRegionSlug?: string,
  regionCategory?: RegionCategory,
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
    ],
    queryFn: () => getRegions(electionConfigSlug!, parentRegionSlug, regionCategory),
    enabled,
  });
}
