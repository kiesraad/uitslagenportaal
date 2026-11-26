import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ElectionConfig } from "@/api/types";
import { Footer } from "@/components/Footer";
import { useRootI18n } from "@/components/LocaleProvider";
import type { Locale } from "@/i18n/locales";
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
   eml_dates: {},
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

/** Shows the locale the root layout renders `<html lang>` in. */
function RootLocale() {
   return <output aria-label="root locale">{useRootI18n().locale}</output>;
}

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

   it("Always offers the technical problem link, even without an election", () => {
      mockElectionConfigs([]);
      renderFooter();

      expect(screen.getByRole("heading", { name: "Technisch probleem op de pagina?" })).toBeInTheDocument();
      expect(screen.getByRole("link", { name: "Technisch probleem melden" })).toHaveAttribute(
         "href",
         expect.stringMatching(/\/api\/report-technical-issue\/$/),
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
      expect(screen.getByRole("link", { name: /Report a technical problem/ })).toBeInTheDocument();
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
      expect(document.cookie).toContain("lang=en");
   });

   // The root layout's `<html lang>` reads this hook, so it has to follow a switch.
   it("Switches the root locale along with the language", async () => {
      mockElectionConfigs([]);
      renderWithProviders(
         <>
            <Footer />
            <RootLocale />
         </>,
         { locale: "nl" },
      );
      const rootLocale = screen.getByRole("status", { name: "root locale" });
      expect(rootLocale).toHaveTextContent("nl");

      fireEvent.click(screen.getByRole("button", { name: "English" }));

      await waitFor(() => expect(rootLocale).toHaveTextContent("en"));
   });
});
