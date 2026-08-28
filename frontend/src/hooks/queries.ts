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

// The query factories carry no `enabled`: a suspense query cannot be disabled, and the route
// loaders that build them always have their parameters.
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
      queryFn: () => getPartyVoteMatrix(electionSlug, partySlug, csbSlug),
   });
}

export function useElectionConfigs() {
   return useQuery({
      queryKey: ["election_configs"],
      queryFn: getElectionConfigs,
   });
}
