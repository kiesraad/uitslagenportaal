import { fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { TimelineDate } from "@/api/types";
import { Timeline } from "@/components/Timeline/Timeline";
import TimelineEntry, { getTimelineDate } from "@/components/Timeline/TimelineEntry";
import { renderWithProviders } from "../../testUtils";

const counted: TimelineDate = { event: "sb_vote_count", date: "2026-03-17T21:00:00+01:00", qualifier: "from" };
const checked: TimelineDate = { event: "csb_check", date: "2026-03-18T10:00:00+01:00", qualifier: "all_day" };
const published: TimelineDate = {
   event: "csb_result_publish",
   date: "2026-03-20T10:00:00+01:00",
   qualifier: "expected",
};

function renderTimeline() {
   return renderWithProviders(
      <Timeline>
         <TimelineEntry key="published" date={published} title="Uitslag publiceren" />
         <TimelineEntry key="counted" date={counted} title="Stemmen tellen" />
         <TimelineEntry key="checked" date={checked} title="Uitslag controleren" />
      </Timeline>,
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
