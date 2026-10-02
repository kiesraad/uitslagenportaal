import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ReportsWithResults from "@/components/ResultsPage/ReportsWithResults";
import { activateLocale, renderWithProviders } from "../../testUtils";

describe("ReportsWithResults", () => {
   it("lists the polling-station zip with how many stations have a report", () => {
      activateLocale("nl");

      renderWithProviders(
         <ReportsWithResults
            title="Brondocumenten"
            description="De telresultaten."
            documents={[]}
            pollingStationPvArchive={{
               url: "/api/tk2025/regions/lisserdam/polling-station-pvs.zip",
               present_count: 12,
               total_count: 29,
               size: 48_000_000,
            }}
         />,
      );

      const link = screen.getByRole("link", { name: /Processen-verbaal van alle stembureaus/ });
      expect(link).toHaveAttribute("href", "/api/tk2025/regions/lisserdam/polling-station-pvs.zip");
      expect(screen.getByText("Handgeschreven verslagen van 12 van de 29 stembureaus")).toBeInTheDocument();
   });
});
