import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import ResultsTimeline from "@/components/ResultsPage/ResultsTimeline";
import type { TimelineEntry } from "@/components/Timeline";
import { renderWithProviders } from "../../testUtils";

const entries: TimelineEntry[] = [
   {
      status: "done",
      title: { nl: "Stemmen tellen", en: "Counting votes" },
      date: "2023-03-15T21:00:00",
      body: { nl: "", en: "" },
   },
   {
      status: "pending",
      title: { nl: "Uitslag vaststellen", en: "Determining the result" },
      date: "2023-03-24T10:00:00",
      body: { nl: "", en: "" },
   },
];

function headingTexts() {
   return screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
}

beforeEach(() => {
   localStorage.clear();
});

describe("ResultsTimeline", () => {
   it("Shows the latest step on top by default", () => {
      renderWithProviders(<ResultsTimeline entries={entries} />);

      expect(screen.getByRole("button", { name: /Laatste stap bovenaan/ })).toBeInTheDocument();
      expect(headingTexts()[0]).toMatch(/^Uitslag vaststellen/);
   });

   it("Starts in the order stored by an earlier page", () => {
      localStorage.setItem("timelineOrder", JSON.stringify("asc"));
      renderWithProviders(<ResultsTimeline entries={entries} />);

      expect(screen.getByRole("button", { name: /Eerste stap bovenaan/ })).toBeInTheDocument();
      expect(headingTexts()[0]).toMatch(/^Stemmen tellen/);
   });

   it("Stores the order when it is flipped", () => {
      renderWithProviders(<ResultsTimeline entries={entries} />);

      fireEvent.click(screen.getByRole("button", { name: /Volgorde omdraaien/ }));

      expect(headingTexts()[0]).toMatch(/^Stemmen tellen/);
      expect(localStorage.getItem("timelineOrder")).toBe(JSON.stringify("asc"));
   });
});
