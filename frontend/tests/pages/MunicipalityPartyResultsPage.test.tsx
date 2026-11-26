import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import type { ElectionConfig, Region } from "@/api/types";
import { electionConfigQuery, regionQuery } from "@/hooks/queries";
import { loadMunicipalityPartyResults } from "@/pages/MunicipalityPage/MunicipalityPartyResultsPage";

const electionConfig = { slug: "ws2023" } as ElectionConfig;

const params = { electionConfigSlug: "ws2023", regionSlug: "654-borsele", csbSlug: "17-scheldestromen" };

const vvdVotes = {
   id: 1,
   valid_votes: 10,
   candidate: null,
   party: { registered_name: "VVD", slug: "vvd", list_number: 1 },
   result_level: "PARTY" as const,
};

/** A client holding what the loader fetches, so it never hits the network. */
function seedGemeente(voteCounts: Region["vote_counts"]) {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   queryClient.setQueryData(electionConfigQuery(params.electionConfigSlug).queryKey, electionConfig);
   queryClient.setQueryData(regionQuery(params, "gsb").queryKey, { vote_counts: voteCounts } as Region);
   return queryClient;
}

function load(queryClient: QueryClient, partySlug: string) {
   return loadMunicipalityPartyResults(queryClient, { params: { ...params, partySlug } });
}

describe("loadMunicipalityPartyResults", () => {
   it("throws a 404 for a party the gemeente has no results for", async () => {
      await expect(load(seedGemeente([vvdVotes]), "onbekend")).rejects.toMatchObject({ status: 404 });
   });

   it("accepts a party the gemeente has results for", async () => {
      await expect(load(seedGemeente([vvdVotes]), "vvd")).resolves.toBeUndefined();
   });

   it("accepts any party while no results are published", async () => {
      await expect(load(seedGemeente([]), "onbekend")).resolves.toBeUndefined();
   });
});
