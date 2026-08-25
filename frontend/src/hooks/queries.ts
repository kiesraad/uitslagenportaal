import { useQuery } from "@tanstack/react-query";
import {
   getElectionConfigBySlug,
   getElectionConfigs,
   getPartyVoteMatrix,
   getRegion,
   getRegions,
} from "../api/endpoints";
import type { PartyVoteMatrix, Region, RegionCategory } from "../api/types";

export const electionConfigQuery = (slug?: string) => ({
   queryKey: ["elections", slug],
   queryFn: () => getElectionConfigBySlug(slug),
   enabled: Boolean(slug),
});

export function useElectionConfig(slug?: string) {
   return useQuery(electionConfigQuery(slug));
}

export function useElectionConfigs() {
   return useQuery({
      queryKey: ["election_configs"],
      queryFn: getElectionConfigs,
   });
}

export function useRegion(
   electionConfigSlug: string | undefined,
   regionSlug: string | undefined,
   csbSlug?: string,
   parentRegionSlug?: string,
) {
   return useQuery<Region>({
      queryKey: ["region", electionConfigSlug, regionSlug, csbSlug ?? null, parentRegionSlug ?? null],
      queryFn: () => getRegion(electionConfigSlug!, regionSlug!, csbSlug, parentRegionSlug),
      enabled: Boolean(electionConfigSlug) && Boolean(regionSlug),
   });
}

export function useRegions(
   electionConfigSlug: string | undefined,
   parentRegionSlug?: string,
   regionCategory?: RegionCategory,
   csbSlug?: string,
) {
   const enabled =
      Boolean(electionConfigSlug) && (Boolean(regionCategory) || Boolean(parentRegionSlug) || Boolean(csbSlug));

   return useQuery({
      queryKey: ["regions", electionConfigSlug, parentRegionSlug ?? null, regionCategory ?? null, csbSlug ?? null],
      queryFn: () => getRegions(electionConfigSlug!, parentRegionSlug, regionCategory, csbSlug),
      enabled,
   });
}

export function usePartyVoteMatrix(
   electionSlug: string | undefined,
   csbSlug: string | undefined,
   partySlug: string | undefined,
) {
   return useQuery<PartyVoteMatrix>({
      queryKey: ["party-vote-matrix", electionSlug, csbSlug, partySlug],
      queryFn: () => getPartyVoteMatrix(electionSlug!, partySlug!, csbSlug!),
      enabled: Boolean(electionSlug) && Boolean(csbSlug) && Boolean(partySlug),
   });
}
