import { apiGet } from "./client";
import type {
   ElectionConfig,
   ElectionConfigsResponse,
   PartyVoteMatrix,
   Region,
   RegionCategory,
   RegionResponse,
} from "./types";

export function getElectionConfigs() {
   return apiGet<ElectionConfigsResponse>("/api/election_configs/");
}

export function getElectionConfigBySlug(slug?: string) {
   return apiGet<ElectionConfig>(`/api/election_configs/${slug}/`);
}

export function getRegions(
   electionConfigSlug: string,
   parentRegionSlug?: string,
   regionCategory?: RegionCategory,
   csbSlug?: string,
) {
   if (!electionConfigSlug || (!parentRegionSlug && !regionCategory && !csbSlug)) {
      throw new Error(
         "getRegions: electionConfigSlug and one of parentRegionSlug, regionCategory, or csbSlug are required.",
      );
   }

   const url = new URL("/api/regions/", window.location.origin);
   url.searchParams.append("election_config", electionConfigSlug);
   if (parentRegionSlug) {
      url.searchParams.append("parent_region", parentRegionSlug);
   }
   if (regionCategory) {
      url.searchParams.append("region_category", regionCategory);
   }
   if (csbSlug) {
      url.searchParams.append("csb", csbSlug);
   }
   return apiGet<RegionResponse>(`${url.pathname}${url.search}`);
}

export function getRegion(electionConfigSlug: string, regionSlug: string, csbSlug?: string, parentRegionSlug?: string) {
   const url = new URL("/api/region/", window.location.origin);
   url.searchParams.append("election_config", electionConfigSlug);
   url.searchParams.append("region", regionSlug);
   if (csbSlug) {
      url.searchParams.append("csb", csbSlug);
   }
   if (parentRegionSlug) {
      url.searchParams.append("parent_region", parentRegionSlug);
   }
   return apiGet<Region>(`${url.pathname}${url.search}`);
}

export function getPartyVoteMatrix(electionSlug: string, partySlug: string, csbSlug: string) {
   const url = new URL("/api/party-result-matrix/", window.location.origin);
   url.searchParams.append("election", electionSlug);
   url.searchParams.append("party", partySlug);
   url.searchParams.append("csb", csbSlug);
   return apiGet<PartyVoteMatrix>(`${url.pathname}${url.search}`);
}
