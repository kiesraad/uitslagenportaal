import { queryOptions, useQuery } from "@tanstack/react-query";
import type { Params } from "react-router";
import {
   getElectionConfigBySlug,
   getElectionConfigs,
   getPartyVoteMatrix,
   getRegion,
   getRegions,
} from "../api/endpoints";
import type { RegionCategory } from "../api/types";

// The query factories carry no `enabled`: a suspense query cannot be disabled, and a route
// loader always has its parameters. Callers whose slug may be absent add the guard themselves.
export function electionConfigQuery(slug?: string) {
   return queryOptions({
      queryKey: ["elections", slug],
      queryFn: () => getElectionConfigBySlug(slug),
   });
}

export function regionQuery({ electionConfigSlug, regionSlug, csbSlug, parentRegionSlug }: Params) {
   return queryOptions({
      queryKey: ["region", electionConfigSlug, regionSlug, csbSlug ?? null, parentRegionSlug ?? null],
      queryFn: () => getRegion(electionConfigSlug, regionSlug, csbSlug, parentRegionSlug),
   });
}

export function regionsQuery({ electionConfigSlug, regionSlug, csbSlug }: Params, regionCategory?: RegionCategory) {
   return queryOptions({
      queryKey: ["regions", electionConfigSlug, regionSlug ?? null, regionCategory ?? null, csbSlug ?? null],
      queryFn: () => getRegions(electionConfigSlug, regionSlug, regionCategory, csbSlug),
   });
}

export function partyVoteMatrixQuery(electionSlug?: string, csbSlug?: string, partySlug?: string) {
   return queryOptions({
      queryKey: ["party-vote-matrix", electionSlug, csbSlug, partySlug],
      queryFn: () => getPartyVoteMatrix(electionSlug!, partySlug!, csbSlug!),
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
   return useQuery({
      ...regionQuery({ electionConfigSlug, regionSlug, csbSlug, parentRegionSlug }),
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
   return useQuery({
      ...partyVoteMatrixQuery(electionSlug, csbSlug, partySlug),
      enabled: Boolean(electionSlug) && Boolean(csbSlug) && Boolean(partySlug),
   });
}
