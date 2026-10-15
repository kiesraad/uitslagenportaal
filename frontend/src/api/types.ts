export type ElectionConfig = {
   slug: string;
   label: string;
   date: string;
   issue_report_opens_at: string;
   issue_report_deadline: string;
   csb_type: RegionCategory;
   single_csb: { region_name: string; slug: string } | null;
   has_hsb: boolean;
   timeline_dates: TimelineDate[];
   report_error_url: string;
   counting_info_url: string;
   voting_url: string;
};

export type ElectionConfigsResponse = ElectionConfig[];

export type TimelineVariant = "CSO" | "DSO" | "DEFAULT";

export type TimelineDateEvent =
   | "sb_vote_count"
   | "candidate_vote_count"
   | "municipality_vote_count"
   | "electoral_district_vote_count"
   | "csb_check"
   | "csb_result_publish";

export type TimelineDateQualifier = "all_day" | "from" | "until" | "expected";

export type TimelineDate = {
   event: TimelineDateEvent;
   date: string;
   qualifier: TimelineDateQualifier;
};

export type ElectionDocument = {
   name: string;
   url: string;
   type: string;
   size: string;
   description: string;
   file_type: string;
   correction_number: number;
};

export type PollingStationPvArchive = {
   url: string;
   present_count: number;
   total_count: number;
   size: number;
};

export type ReportingLevel = "gsb" | "hsb" | "csb" | "sb";

export type RegionCategory = "STAAT" | "WATERSCHAP" | "KIESKRING" | "GEMEENTE" | "PROVINCIE" | "STEMBUREAU";

export type VoterTurnoutCategory = "REJECTED" | "UNCOUNTED";

export type VoterTurnoutCount = {
   category: VoterTurnoutCategory;
   reason_code: string;
   votes: number;
};

export type Region = {
   region_name: string;
   slug: string;
   vote_counts: VoteCounts;
   voter_turnout_counts?: VoterTurnoutCount[];
   timeline_variant?: TimelineVariant;
   documents?: ElectionDocument[];
   polling_station_pv_archive?: PollingStationPvArchive | null;
   certified_document_url?: string | null;
   certified_document_preview_url?: string | null;
   region_category: RegionCategory;
   results_available_at: string | null;
   csb_name?: string | null;
   csb_slug?: string | null;
   election_slug?: string;
   station_number?: number | null;
};

export type RegionResponse = Region[];

export type Party = {
   registered_name: string;
   slug: string;
   list_number: number | null;
};

export type Candidate = {
   position: number;
   initials: string;
   first_name: string | null;
   name_prefix: string | null;
   last_name: string;
};

export type VoteResultLevel = "PARTY" | "CANDIDATE";

export type VoteCount = {
   valid_votes: number;
   id: number;
   candidate: Candidate | null;
   party: Party;
   result_level: VoteResultLevel;
};

export type VoteCounts = VoteCount[];

export type PartyVoteMatrixColumn = {
   slug: string;
   region_name: string;
};

export type PartyVoteMatrixRow = {
   candidate: Candidate;
   total: number | null;
   votes: Record<string, number | null>;
};

export type PartyVoteMatrixTotals = {
   total: number | null;
   votes: Record<string, number | null>;
};

export type PartyVoteMatrix = {
   party: Party;
   csb?: Pick<Region, "region_name" | "slug">;
   hsb?: Pick<Region, "region_name" | "slug">;
   columns: PartyVoteMatrixColumn[];
   rows: PartyVoteMatrixRow[];
   totals: PartyVoteMatrixTotals;
};
