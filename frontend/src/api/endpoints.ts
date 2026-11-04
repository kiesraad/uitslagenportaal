import { apiGet } from "./client";
import type {
   ElectionConfig,
   ElectionConfigsResponse,
   PartyVoteMatrix,
   Region,
   RegionCategory,
   RegionResponse,
   ReportingLevel,
} from "./types";

export function getElectionConfigs() {
   return apiGet<ElectionConfigsResponse>("/api/election_configs/");
}

export function getElectionConfigBySlug(slug?: string) {
   return apiGet<ElectionConfig>(`/api/election_configs/${slug}/`);
}

export function getRegions(
   electionConfigSlug?: string,
   parentRegionSlug?: string,
   regionCategory?: RegionCategory,
   csbSlug?: string,
) {
   if (!electionConfigSlug || (!parentRegionSlug && !regionCategory && !csbSlug)) {
      throw new Error(
         "getRegions: electionConfigSlug and one of parentRegionSlug, regionCategory, or csbSlug are required.",
      );
   }

   const searchParams = new URLSearchParams();
   if (parentRegionSlug) {
      searchParams.append("parent_region", parentRegionSlug);
   }
   if (regionCategory) {
      searchParams.append("region_category", regionCategory);
   }
   if (csbSlug) {
      searchParams.append("csb", csbSlug);
   }
   return apiGet<RegionResponse>(`/api/${electionConfigSlug}/regions/?${searchParams}`);
}

export function getRegion(
   electionConfigSlug?: string,
   regionSlug?: string,
   csbSlug?: string,
   parentRegionSlug?: string,
   level?: ReportingLevel,
) {
   if (!electionConfigSlug || !regionSlug || !level) {
      throw new Error("getRegion: electionConfigSlug, regionSlug and level are required.");
   }

   const searchParams = new URLSearchParams({ level });
   if (csbSlug) {
      searchParams.append("csb", csbSlug);
   }
   if (parentRegionSlug) {
      searchParams.append("parent_region", parentRegionSlug);
   }
   return apiGet<Region>(`/api/${electionConfigSlug}/regions/${regionSlug}?${searchParams}`);
}

export function getCSBPartyVoteMatrix(electionSlug?: string, partySlug?: string, csbSlug?: string) {
   if (!electionSlug || !partySlug || !csbSlug) {
      throw new Error("getCSBPartyVoteMatrix: electionSlug, partySlug and csbSlug are required.");
   }

   const searchParams = new URLSearchParams({ election: electionSlug, party: partySlug, csb: csbSlug });
   return apiGet<PartyVoteMatrix>(`/api/party-result-matrix/?${searchParams}`);
}

export function getHSBPartyVoteMatrix(electionSlug?: string, partySlug?: string, hsbSlug?: string) {
   if (!electionSlug || !partySlug || !hsbSlug) {
      throw new Error("getHSBPartyVoteMatrix: electionSlug, partySlug and hsbSlug are required.");
   }

   const searchParams = new URLSearchParams({ election: electionSlug, party: partySlug, hsb: hsbSlug });
   return apiGet<PartyVoteMatrix>(`/api/hsb-party-result-matrix/?${searchParams}`);
}
