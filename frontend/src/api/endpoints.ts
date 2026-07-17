import { apiGet } from './client'
import type { ElectionConfig, ElectionConfigsResponse, Region, RegionCategory, RegionResponse } from './types'

export function getElectionConfigs() {
  return apiGet<ElectionConfigsResponse>('/api/election_configs/')
}

export function getElectionConfigBySlug(slug: string) {
  return apiGet<ElectionConfig>(`/api/election_configs/${slug}`)
}

export function getRegions(
  electionConfigSlug: string,
  parentRegionSlug?: string,
  regionCategory?: RegionCategory
) {
  if (!electionConfigSlug || (!parentRegionSlug && !regionCategory)) {
    throw new Error('getRegions: electionConfigSlug and one of parentRegionSlug or regionCategory are required.')
  }

  let url = `/api/regions?election_config=${encodeURIComponent(electionConfigSlug)}`;
  if (parentRegionSlug) {
    url += `&parent_region=${encodeURIComponent(parentRegionSlug)}`;
  }
  if (regionCategory) {
    url += `&region_category=${encodeURIComponent(regionCategory)}`;
  }
  return apiGet<RegionResponse>(url);
}

export function getRegion(electionConfigSlug: string, regionSlug: string) {
  return apiGet<Region>(`/api/region?election_config=${electionConfigSlug}&region=${regionSlug}`)
}

