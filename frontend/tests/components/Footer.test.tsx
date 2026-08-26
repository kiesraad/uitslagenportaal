import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ElectionConfig } from "@/api/types";
import { Footer } from "@/components/Footer";
import type { Locale } from "@/i18n/locales";
import { renderWithProviders } from "../testUtils";

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00",
   csb_type: "WATERSCHAP",
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

function mockElectionConfigs(configs: ElectionConfig[]) {
   vi.stubGlobal(
      "fetch",
      vi.fn(() =>
         Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve(configs),
         } as Response),
      ),
   );
}

function renderFooter(locale: Locale = "nl") {
   return renderWithProviders(<Footer />, { locale });
}

beforeEach(() => {
   localStorage.clear();
});

afterEach(() => {
   vi.unstubAllGlobals();
});

describe("Footer", () => {
   it("Renders the copyright notice with the current year", () => {
      mockElectionConfigs([]);
      renderFooter();

      const currentYear = new Date().getFullYear();
      expect(screen.getByText(`© ${currentYear} De Kiesraad`)).toBeInTheDocument();
   });

   it("Always offers the shared report link, even without an election", () => {
      mockElectionConfigs([]);
      renderFooter();

      expect(screen.getByRole("link", { name: /Melding maken/ })).toHaveAttribute(
         "href",
         "https://www.kiesraad.nl/service/contact",
      );
   });

   it("Always links to Kiesraad.nl", () => {
      mockElectionConfigs([]);
      renderFooter();

      expect(screen.getByRole("link", { name: /Kiesraad\.nl/ })).toHaveAttribute("href", "https://www.kiesraad.nl/");
   });

   it("Shows the election label and links when a single election is available", async () => {
      mockElectionConfigs([electionConfig]);
      renderFooter();

      expect(await screen.findByRole("heading", { name: electionConfig.label })).toBeInTheDocument();

      expect(screen.getByRole("link", { name: /Uitleg over telproces/ })).toHaveAttribute(
         "href",
         electionConfig.counting_info_url,
      );
      expect(screen.getByRole("link", { name: /Stemmen/ })).toHaveAttribute("href", electionConfig.voting_url);
   });

   it("Omits links whose url is not configured", async () => {
      mockElectionConfigs([{ ...electionConfig, counting_info_url: "", voting_url: "" }]);
      renderFooter();

      expect(await screen.findByRole("heading", { name: electionConfig.label })).toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Uitleg over telproces/ })).not.toBeInTheDocument();
      expect(screen.queryByRole("link", { name: /Stemmen/ })).not.toBeInTheDocument();
   });

   it("Renders the footer links in English when that locale is active", async () => {
      mockElectionConfigs([electionConfig]);
      renderFooter("en");

      expect(await screen.findByRole("link", { name: /About the counting process/ })).toBeInTheDocument();
      expect(screen.getByText("This website in other languages:")).toBeInTheDocument();
      expect(screen.getByRole("link", { name: /Report an issue/ })).toBeInTheDocument();
   });

   it("Offers the other language and switches to it when clicked", async () => {
      mockElectionConfigs([]);
      renderFooter("nl");

      // On Dutch the button offers English, each language named in its own tongue.
      const toggle = screen.getByRole("button", { name: "English" });
      expect(toggle).toHaveAttribute("lang", "en");

      fireEvent.click(toggle);

      await waitFor(() => {
         expect(screen.getByText("This website in other languages:")).toBeInTheDocument();
      });
      // The switcher now offers the way back, and the choice is persisted.
      expect(screen.getByRole("button", { name: "Nederlands" })).toBeInTheDocument();
      expect(localStorage.getItem("lang")).toBe("en");
      expect(document.documentElement.lang).toBe("en");
   });
});
