import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ElectionDocument } from "@/api/types";
import ReportsWithResults from "@/components/ResultsPage/ReportsWithResults";
import { activateLocale, renderWithProviders } from "../../testUtils";

function correction(overrides: Partial<ElectionDocument>): ElectionDocument {
   return {
      name: "correction.pdf",
      url: "/api/documents/1/download/",
      type: "pdf",
      size: "1024",
      description: "",
      file_type: "PDF_NA14-2",
      correction_number: 1,
      metadata: {},
      ...overrides,
   };
}

describe("ReportsWithResults", () => {
   it("lists the polling-station zip with how many stations have a report", () => {
      activateLocale("nl");

      renderWithProviders(
         <ReportsWithResults
            title="Brondocumenten"
            description="De telresultaten."
            documents={[
               correction({
                  url: "/api/documents/3/download/",
                  type: "zip",
                  file_type: "PDF_SB-ZIP",
                  metadata: { total: 29, present: 12 },
               }),
            ]}
         />,
      );

      const link = screen.getByRole("link", { name: /^Processen-verbaal van alle stembureaus \(zip/ });
      expect(link).toHaveAttribute("href", "/api/documents/3/download/");
      expect(screen.getByText("Handgeschreven verslagen van 12 van de 29 stembureaus")).toBeInTheDocument();
   });

   it("numbers every correction past the first, so stacked ones are told apart", () => {
      activateLocale("nl");

      renderWithProviders(
         <ReportsWithResults
            title="Brondocumenten"
            description="De telresultaten."
            documents={[
               correction({ url: "/api/documents/1/download/", correction_number: 1 }),
               correction({ url: "/api/documents/2/download/", correction_number: 2 }),
            ]}
         />,
      );

      expect(
         screen.getByRole("link", { name: /^Corrigendum proces-verbaal gemeentelijk stembureau \(pdf/ }),
      ).toHaveAttribute("href", "/api/documents/1/download/");
      expect(
         screen.getByRole("link", { name: /^Corrigendum proces-verbaal gemeentelijk stembureau 2 \(pdf/ }),
      ).toHaveAttribute("href", "/api/documents/2/download/");
   });
});
