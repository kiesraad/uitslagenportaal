import type { VoteCount, VoteCounts } from "../api/types";

export function getPartyLevelVoteCounts(voteCounts: VoteCounts | undefined): VoteCounts {
   return voteCounts?.filter((voteCount) => voteCount.result_level === "PARTY") ?? [];
}

export function getPartyVoteCount(voteCounts: VoteCounts | undefined, partySlug: string): VoteCount | undefined {
   return getPartyLevelVoteCounts(voteCounts).find((voteCount) => voteCount.party.slug === partySlug);
}

export function getCandidateVoteCountsForParty(voteCounts: VoteCounts | undefined, partySlug: string): VoteCounts {
   return (
      voteCounts?.filter((voteCount) => voteCount.party.slug === partySlug && voteCount.result_level === "CANDIDATE") ??
      []
   ).sort((a, b) => (a.candidate?.position ?? 0) - (b.candidate?.position ?? 0));
}

export function hasParty(voteCounts: VoteCounts | undefined, partySlug: string): boolean {
   return voteCounts?.some((voteCount) => voteCount.party.slug === partySlug) ?? false;
}
