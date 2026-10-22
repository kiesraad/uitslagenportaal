import { fireEvent, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ElectionDocument, TimelineDate } from "@/api/types";
import { Timeline, TimelineContext, type TimelineContextProps } from "@/components/Timeline/Timeline";
import TimelineEntry, { getTimelineDate, type TimelineEntryProps } from "@/components/Timeline/TimelineEntry";
import { renderWithProviders } from "../../testUtils";

const counted: TimelineDate = { event: "sb_vote_count", date: "2026-03-17T21:00:00+01:00", qualifier: "from" };
const checked: TimelineDate = { event: "csb_check", date: "2026-03-18T10:00:00+01:00", qualifier: "all_day" };
const published: TimelineDate = {
   event: "csb_result_publish",
   date: "2026-03-20T10:00:00+01:00",
   qualifier: "expected",
};

// Entries are written latest step first.
function renderTimeline() {
   return renderWithProviders(
      <Timeline dates={[]}>
         <TimelineEntry key="published" date={published} title="Uitslag publiceren" />
         <TimelineEntry key="checked" date={checked} title="Uitslag controleren" />
         <TimelineEntry key="counted" date={counted} title="Stemmen tellen" />
      </Timeline>,
   );
}

function document(overrides: Partial<ElectionDocument>): ElectionDocument {
   return {
      name: "telling.xml",
      url: "/api/documents/1/download/",
      type: "xml",
      size: "1024",
      description: "",
      file_type: "EML510b",
      correction_number: 1,
      metadata: {},
      ...overrides,
   };
}

function renderEntry(entry: ReactElement<TimelineEntryProps>, context: Partial<TimelineContextProps> = {}) {
   return renderWithProviders(
      <TimelineContext value={{ dates: [], ...context }}>
         <ol>{entry}</ol>
      </TimelineContext>,
   );
}

function headingTexts() {
   return screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
}

beforeEach(() => {
   localStorage.clear();
   vi.useFakeTimers({ toFake: ["Date"] });
   vi.setSystemTime(new Date("2026-03-18T12:00:00+01:00"));
});

afterEach(() => {
   vi.useRealTimers();
});

describe("Timeline", () => {
   it("shows the latest step on top by default", () => {
      renderTimeline();

      expect(screen.getByRole("button", { name: /Laatste stap bovenaan/ })).toBeInTheDocument();
      expect(headingTexts()).toEqual([
         expect.stringMatching(/^Uitslag publiceren/),
         expect.stringMatching(/^Uitslag controleren/),
         expect.stringMatching(/^Stemmen tellen/),
      ]);
   });

   it("starts in the order stored by an earlier page", () => {
      localStorage.setItem("timeline-order-desc", JSON.stringify(false));
      renderTimeline();

      expect(screen.getByRole("button", { name: /Eerste stap bovenaan/ })).toBeInTheDocument();
      expect(headingTexts()[0]).toMatch(/^Stemmen tellen/);
   });

   it("stores the order when it is flipped", () => {
      renderTimeline();

      fireEvent.click(screen.getByRole("button", { name: /Volgorde omdraaien/ }));

      expect(headingTexts()[0]).toMatch(/^Stemmen tellen/);
      expect(localStorage.getItem("timeline-order-desc")).toBe(JSON.stringify(false));
   });
});

describe("TimelineEntry", () => {
   it("derives its status from the day of its date", () => {
      renderTimeline();

      expect(screen.getByRole("heading", { name: "Stemmen tellen, afgerond" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Uitslag controleren, bezig" })).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Uitslag publiceren, nog niet gestart" })).toBeInTheDocument();
   });

   it("is pending when its date cannot be parsed", () => {
      renderEntry(<TimelineEntry date={{ ...checked, date: "later" }} title="Uitslag controleren" />);

      expect(screen.getByRole("heading", { name: "Uitslag controleren, nog niet gestart" })).toBeInTheDocument();
   });

   it("takes the date for its event from the timeline", () => {
      renderEntry(<TimelineEntry event="sb_vote_count" title="Stemmen tellen" />, { dates: [counted] });

      expect(screen.getByRole("heading", { name: "Stemmen tellen, afgerond" })).toBeInTheDocument();
   });

   it("lists only the timeline documents of its own types", () => {
      renderEntry(<TimelineEntry date={counted} title="Stemmen tellen" document_types={["EML510b"]} />, {
         documents: [
            document({ url: "/api/documents/1/download/", file_type: "EML510b" }),
            document({ url: "/api/documents/2/download/", file_type: "EML510c" }),
         ],
      });

      expect(screen.getByRole("link", { name: /^EML_NL tellingbestand 510b/ })).toHaveAttribute(
         "href",
         "/api/documents/1/download/",
      );
      expect(screen.queryByRole("link", { name: /510c/ })).not.toBeInTheDocument();
   });
});

describe("getTimelineDate", () => {
   it("returns the date for the event", () => {
      expect(getTimelineDate([counted, checked], "csb_check")).toBe(checked);
   });

   it("falls back to today, all day, for a missing event", () => {
      expect(getTimelineDate([counted], "csb_check")).toEqual({
         event: "csb_check",
         date: "2026-03-18T11:00:00.000Z",
         qualifier: "all_day",
      });
   });
});
