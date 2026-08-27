import { queryOptions, useQuery } from "@tanstack/react-query";
import type { Params } from "react-router";
import {
   getElectionConfigBySlug,
   getElectionConfigs,
   getPartyVoteMatrix,
   getRegion,
   getRegions,
} from "../api/endpoints";
import type { PartyVoteMatrix, Region, RegionCategory } from "../api/types";

// The query factories carry no `enabled`: a suspense query cannot be disabled, and a route
// loader always has its parameters. Callers whose slug may be absent add the guard themselves.
export function electionConfigQuery(slug?: string) {
   return queryOptions({
      queryKey: ["elections", slug],
      queryFn: () => getElectionConfigBySlug(slug),
   });
}

export function regionsQuery(params: Params, regionCategory?: RegionCategory) {
   return queryOptions({
      queryKey: [
         "regions",
         params?.electionConfigSlug,
         params?.regionSlug ?? null,
         regionCategory ?? null,
         params?.csbSlug ?? null,
      ],
      queryFn: () => getRegions(params?.electionConfigSlug, params?.regionSlug, regionCategory, params?.csbSlug),
   });
}

export function useElectionConfig(slug?: string) {
   return useQuery({ ...electionConfigQuery(slug), enabled: Boolean(slug) });
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
      ...regionsQuery({ electionConfigSlug, regionSlug: parentRegionSlug, csbSlug }, regionCategory),
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
