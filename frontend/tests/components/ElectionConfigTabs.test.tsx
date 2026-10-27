import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ElectionConfig } from "@/api/types";
import ElectionConfigTabs from "@/components/ElectionConfigTabs";
import { renderWithProviders } from "../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00",
   csb_type: "WATERSCHAP",
   single_csb: null,
   has_hsb: false,
   timeline_dates: [],
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

describe("ElectionConfigTabs", () => {
   it("links gemeente and CSB lists, and omits kieskringen when the election has none", () => {
      renderWithProviders(<ElectionConfigTabs electionConfig={electionConfig} />, {
         initialEntries: ["/ws2023/gsb"],
      });

      expect(screen.getByRole("link", { name: "Gemeente" })).toHaveAttribute("href", "/ws2023/gsb");
      expect(screen.getByRole("link", { name: "Waterschappen" })).toHaveAttribute("href", "/ws2023/csb");
      expect(screen.queryByRole("link", { name: "Kieskringen" })).not.toBeInTheDocument();
   });

   it("shows kieskringen when the election has HSBs", () => {
      renderWithProviders(<ElectionConfigTabs electionConfig={{ ...electionConfig, has_hsb: true }} />, {
         initialEntries: ["/ws2023/hsb"],
      });

      expect(screen.getByRole("link", { name: "Kieskringen" })).toHaveAttribute("href", "/ws2023/hsb");
      expect(screen.getByRole("link", { name: "Kieskringen" })).toHaveAttribute("aria-current", "page");
   });

   it("names the CSB tab after the election's only CSB", () => {
      renderWithProviders(
         <ElectionConfigTabs
            electionConfig={{
               ...electionConfig,
               slug: "tk2025",
               csb_type: "STAAT",
               single_csb: { region_name: "Nederland", slug: "nederland" },
            }}
         />,
         { initialEntries: ["/tk2025/gsb"] },
      );

      expect(screen.getByRole("link", { name: "Nederland" })).toHaveAttribute("href", "/tk2025/csb");
   });

   it("shows kieskringen and Nederland for a TK election before any results are imported", () => {
      renderWithProviders(
         <ElectionConfigTabs electionConfig={{ ...electionConfig, slug: "tk2025", csb_type: "STAAT" }} />,
         { initialEntries: ["/tk2025/gsb"] },
      );

      expect(screen.getByRole("link", { name: "Kieskringen" })).toHaveAttribute("href", "/tk2025/hsb");
      expect(screen.getByRole("link", { name: "Nederland" })).toHaveAttribute("href", "/tk2025/csb");
   });
});
