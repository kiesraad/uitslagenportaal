import { describe, expect, it } from "vitest";

import type { VoteCounts } from "@/api/types";
import { hasParty } from "@/utils/voteCounts";

const voteCounts = [
   { id: 1, valid_votes: 10, candidate: null, party: { slug: "cda" }, result_level: "PARTY" },
   { id: 2, valid_votes: 4, candidate: null, party: { slug: "cda" }, result_level: "CANDIDATE" },
   { id: 3, valid_votes: 7, candidate: null, party: { slug: "bbb" }, result_level: "PARTY" },
] as unknown as VoteCounts;

describe("hasParty", () => {
   it("finds a party that is present in the results", () => {
      expect(hasParty(voteCounts, "cda")).toBe(true);
      expect(hasParty(voteCounts, "bbb")).toBe(true);
   });

   it("reports a party slug that does not appear in the results", () => {
      expect(hasParty(voteCounts, "partij-van-de-vrienden")).toBe(false);
   });

   it("matches on candidate-level rows too, not just party-level ones", () => {
      const candidateOnly = [voteCounts[1]] as VoteCounts;
      expect(hasParty(candidateOnly, "cda")).toBe(true);
   });

   it("returns false for missing or empty vote counts", () => {
      expect(hasParty(undefined, "cda")).toBe(false);
      expect(hasParty([] as VoteCounts, "cda")).toBe(false);
   });
});
