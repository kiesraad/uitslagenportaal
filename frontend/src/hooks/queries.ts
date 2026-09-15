import { queryOptions, useQuery } from "@tanstack/react-query";
import type { Params } from "react-router";
import {
   getCSBPartyVoteMatrix,
   getElectionConfigBySlug,
   getElectionConfigs,
   getHSBPartyVoteMatrix,
   getRegion,
   getRegions,
} from "../api/endpoints";
import type { RegionCategory, ReportingLevel } from "../api/types";

// The query factories carry no `enabled`: a suspense query cannot be disabled, and the route
// loaders that build them always have their parameters.
export function electionConfigQuery(slug?: string) {
   return queryOptions({
      queryKey: ["elections", slug],
      queryFn: () => getElectionConfigBySlug(slug),
   });
}

export function regionQuery(
   { electionConfigSlug, regionSlug, csbSlug, parentRegionSlug }: Params,
   level: ReportingLevel,
) {
   return queryOptions({
      queryKey: ["region", electionConfigSlug, regionSlug, csbSlug ?? null, parentRegionSlug ?? null, level],
      queryFn: () => getRegion(electionConfigSlug, regionSlug, csbSlug, parentRegionSlug, level),
   });
}

export function regionsQuery(
   { electionConfigSlug, regionSlug, csbSlug }: Params,
   regionCategory?: RegionCategory,
   hasOwnResults?: boolean,
) {
   return queryOptions({
      queryKey: [
         "regions",
         electionConfigSlug,
         regionSlug ?? null,
         regionCategory ?? null,
         csbSlug ?? null,
         hasOwnResults ?? null,
      ],
      queryFn: () => getRegions(electionConfigSlug, regionSlug, regionCategory, csbSlug, hasOwnResults),
   });
}

export function csbPartyVoteMatrixQuery(electionSlug?: string, csbSlug?: string, partySlug?: string) {
   return queryOptions({
      queryKey: ["party-vote-matrix", electionSlug, csbSlug, partySlug],
      queryFn: () => getCSBPartyVoteMatrix(electionSlug, partySlug, csbSlug),
   });
}

export function hsbPartyVoteMatrixQuery(electionSlug?: string, hsbSlug?: string, partySlug?: string) {
   return queryOptions({
      queryKey: ["hsb-party-vote-matrix", electionSlug, hsbSlug, partySlug],
      queryFn: () => getHSBPartyVoteMatrix(electionSlug, partySlug, hsbSlug),
   });
}

export function useElectionConfigs() {
   return useQuery({
      queryKey: ["election_configs"],
      queryFn: getElectionConfigs,
   });
}
