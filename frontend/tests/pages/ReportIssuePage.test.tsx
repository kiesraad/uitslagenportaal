import { QueryClient } from "@tanstack/react-query";
import { act, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { ElectionConfig } from "@/api/types";
import { electionConfigQuery } from "@/hooks/queries";
import { ReportIssuePage } from "@/pages/ReportIssuePage";
import { renderWithProviders } from "../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-10T12:45:00+01:00",
   csb_type: "WATERSCHAP",
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

/**
 * Mounts the page the way its route does: the loader hands it the query, whose data is
 * already in the cache. `staleTime` keeps the suspense query from refetching behind the
 * assertions, so the page renders in one synchronous pass.
 */
function renderReportIssuePage(config: ElectionConfig = electionConfig, locale: "nl" | "en" = "nl") {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   const query = electionConfigQuery(config.slug);
   queryClient.setQueryData(query.queryKey, config);

   return renderWithProviders(<ReportIssuePage />, {
      locale,
      initialEntries: [`/${config.slug}/fout-melden`],
      path: "/:electionConfigSlug/fout-melden",
      loaderData: { electionConfigQuery: query },
      queryClient,
   });
}

beforeEach(() => {
   vi.useFakeTimers();
   vi.setSystemTime(new Date("2026-12-10T12:00:00+01:00"));
});

afterEach(() => {
   vi.useRealTimers();
});

describe("ReportIssuePage", () => {
   it("updates the deadline heading as time passes", () => {
      renderReportIssuePage();

      expect(
         screen.getByRole("heading", { name: "U heeft nog 45 minuten om een melding te maken" }),
      ).toBeInTheDocument();

      act(() => {
         vi.advanceTimersByTime(60_000);
      });

      expect(
         screen.getByRole("heading", { name: "U heeft nog 44 minuten om een melding te maken" }),
      ).toBeInTheDocument();
   });

   it("disables the report button when the deadline passes", () => {
      renderReportIssuePage({ ...electionConfig, issue_report_deadline: "2026-12-10T12:00:30+01:00" });

      expect(screen.getByText("Meld een fout")).not.toHaveAttribute("aria-disabled", "true");

      act(() => {
         vi.advanceTimersByTime(30_000);
      });

      expect(screen.getByRole("heading", { name: "U kunt geen fout meer melden" })).toBeInTheDocument();
      expect(screen.getByText("Meld een fout")).toHaveAttribute("aria-disabled", "true");
   });

   it("renders the deadline heading in English when that locale is active", () => {
      renderReportIssuePage(electionConfig, "en");

      expect(screen.getByRole("heading", { name: "You have 45 more minutes to submit a report" })).toBeInTheDocument();
   });
});
