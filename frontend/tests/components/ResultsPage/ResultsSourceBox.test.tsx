import { QueryClient } from "@tanstack/react-query";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { type ReactElement, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ElectionConfig, TocEntry } from "@/api/types";
import PvPageLink from "@/components/ResultsPage/PvPageLink";
import ResultsPageColumns from "@/components/ResultsPage/ResultsPageColumns";
import ResultsSourceBox from "@/components/ResultsPage/ResultsSourceBox";
import { electionConfigQuery } from "@/hooks/queries";
import { renderWithProviders } from "../../testUtils";

// PDF.js needs a canvas and a worker, which jsdom does not have.
type PdfDocumentProps = { file: string; pageNumber: number; onPageChange: (page: number) => void };
const PdfDocument = vi.hoisted(() => vi.fn((_props: PdfDocumentProps) => null));
vi.mock("@/components/ResultsPage/PdfDocument", () => ({ default: PdfDocument }));

// jsdom has no matchMedia. `screenWidth.narrow()` makes the window drop below the two-column breakpoint.
const screenWidth = vi.hoisted(() => ({ matches: true, onChange: () => {}, narrow: () => {} }));
vi.stubGlobal("matchMedia", () => ({
   get matches() {
      return screenWidth.matches;
   },
   addEventListener: (_type: string, listener: () => void) => {
      screenWidth.onChange = listener;
   },
   removeEventListener: () => {},
}));
screenWidth.narrow = () => {
   screenWidth.matches = false;
   screenWidth.onChange();
};

const electionConfig: ElectionConfig = {
   slug: "ws2023",
   label: "Waterschapsverkiezingen 2023",
   date: "2023-12-15T11:00:00",
   issue_report_opens_at: "2026-12-08T09:00:00",
   issue_report_deadline: "2026-12-14T10:00:00+01:00",
   csb_type: "WATERSCHAP",
   single_csb: null,
   has_hsb: false,
   timeline_dates: [],
   eml_dates: {},
   report_error_url: "https://example.test/melding",
   counting_info_url: "https://example.test/telproces",
   voting_url: "https://example.test/stemmen",
};

function StatefulBox(props: { previewUrl?: string | null; documentUrl?: string | null }) {
   const [page, setPage] = useState<number | null>(null);
   return <ResultsSourceBox {...props} viewerPage={page} onViewerPageChange={setPage} />;
}

function renderWithConfig(ui: ReactElement, locale: "nl" | "en" = "nl") {
   const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Number.POSITIVE_INFINITY } },
   });
   const query = electionConfigQuery(electionConfig.slug);
   queryClient.setQueryData(query.queryKey, electionConfig);

   return renderWithProviders(ui, {
      locale,
      initialEntries: [`/${electionConfig.slug}/gsb/lisserdam`],
      path: "/:electionConfigSlug/*",
      queryClient,
   });
}

function renderBox(locale: "nl" | "en" = "nl", previewUrl?: string | null, documentUrl?: string | null) {
   return renderWithConfig(<StatefulBox previewUrl={previewUrl} documentUrl={documentUrl} />, locale);
}

describe("ResultsSourceBox", () => {
   beforeEach(() => {
      PdfDocument.mockClear();
      screenWidth.matches = true;
   });

   it("Only says the certified election document is not published yet when the region has none", () => {
      renderBox();

      expect(
         screen.getByRole("heading", { level: 2, name: "Waar komen deze telresultaten vandaan?" }),
      ).toBeInTheDocument();
      expect(screen.getByText(/Momenteel is het proces-verbaal nog niet gepubliceerd/)).toBeInTheDocument();
      expect(screen.queryByRole("img", { name: "Proces-verbaal" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
   });

   it("Opens the full certified election document from the picture and from the link", () => {
      const previewUrl = "/api/certified-documents/7/preview/";
      const documentUrl = "/api/certified-documents/7/";
      renderBox("nl", previewUrl, documentUrl);

      for (const image of screen.getAllByRole("img", { name: "Proces-verbaal" })) {
         expect(image).toHaveAttribute("src", previewUrl);
      }
      const links = screen.getAllByRole("link", { name: /proces-verbaal/i });
      expect(links).toHaveLength(2);
      for (const link of links) {
         expect(link).toHaveAttribute("href", documentUrl);
         expect(link).toHaveAttribute("target", "_blank");
      }
      expect(screen.getByRole("link", { name: /Meld een fout of iets dat niet klopt/ })).toHaveAttribute(
         "href",
         "/ws2023/fout-melden",
      );
      expect(screen.getByText(/14 december om 10:00/)).toBeInTheDocument();
   });

   it("Opens the viewer from the picture and returns focus to it when closed", () => {
      renderBox("nl", "/api/certified-documents/7/preview/", "/api/certified-documents/7/");

      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));

      expect(screen.getByRole("heading", { level: 2, name: "Proces-verbaal" })).toHaveFocus();
      expect(screen.queryByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Sluiten" }));

      expect(screen.getByRole("button", { name: "Proces-verbaal" })).toHaveFocus();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });

   it("Closes the viewer when the window narrows to one column", () => {
      renderBox("nl", "/api/certified-documents/7/preview/", "/api/certified-documents/7/");
      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));
      expect(screen.getByRole("button", { name: "Sluiten" })).toBeInTheDocument();

      act(() => screenWidth.narrow());

      expect(screen.queryByRole("button", { name: "Sluiten" })).not.toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });

   it("Loads the PDF only once the viewer opens, and hands it the document", async () => {
      const documentUrl = "/api/certified-documents/7/";
      renderBox("nl", "/api/certified-documents/7/preview/", documentUrl);

      // One column links to the PDF instead of opening the viewer.
      const narrowLink = screen.getByRole("link", { name: /^Proces-verbaal ?\(opent in nieuw venster\)$/ });
      expect(narrowLink).toHaveAttribute("href", documentUrl);
      expect(narrowLink).toHaveAttribute("target", "_blank");
      expect(PdfDocument).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));

      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      expect(PdfDocument.mock.lastCall?.[0].file).toBe(`${documentUrl}?stream`);
   });

   it("Says the certified election document is not published when only the document exists", () => {
      renderBox("nl", null, "/api/certified-documents/7/");

      expect(screen.getByText(/Momenteel is het proces-verbaal nog niet gepubliceerd/)).toBeInTheDocument();
      expect(screen.queryByRole("img", { name: "Proces-verbaal" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
   });

   it("Says the certified election document is not published when only the preview exists", () => {
      renderBox("nl", "/api/certified-documents/7/preview/", null);

      expect(screen.getByText(/Momenteel is het proces-verbaal nog niet gepubliceerd/)).toBeInTheDocument();
      expect(screen.queryByRole("img", { name: "Proces-verbaal" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
   });

   it("Renders the source box in English when that locale is active", () => {
      renderBox("en");

      expect(
         screen.getByRole("heading", { level: 2, name: "Where do these counting results come from?" }),
      ).toBeInTheDocument();
      expect(screen.getByText(/The certified election results have not been published yet/)).toBeInTheDocument();
   });
});

describe("PvPageLink", () => {
   const previewUrl = "/api/certified-documents/7/preview/";
   const documentUrl = "/api/certified-documents/7/";
   const toc: TocEntry[] = [
      { page: 1, content: "cover" },
      { page: 3, content: "admitted-voters" },
   ];

   function columns(url = documentUrl, documentToc: TocEntry[] | null = toc) {
      return (
         <ResultsPageColumns previewUrl={previewUrl} documentUrl={url} documentToc={documentToc}>
            <PvPageLink content="admitted-voters" />
         </ResultsPageColumns>
      );
   }

   beforeEach(() => {
      PdfDocument.mockClear();
      screenWidth.matches = true;
   });

   it("Shows no link while the page is unknown", () => {
      renderWithConfig(columns(documentUrl, null));

      expect(screen.queryByText("Toon in proces-verbaal")).not.toBeInTheDocument();
   });

   it("Opens the viewer at the page, and jumps there when it is open", async () => {
      renderWithConfig(columns());

      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3);

      act(() => PdfDocument.mock.lastCall?.[0].onPageChange(1));
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(1);

      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3);
   });

   it("Opens the PDF at the page in a new tab on one column", () => {
      renderWithConfig(columns());

      const link = screen.getByRole("link", { name: /Toon in proces-verbaal/ });
      expect(link).toHaveAttribute("href", `${documentUrl}#page=3`);
      expect(link).toHaveAttribute("target", "_blank");
   });

   it("Starts at page 1 when the viewer shows another document", async () => {
      const { rerender } = renderWithConfig(columns());
      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      await waitFor(() => expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3));

      rerender(columns("/api/certified-documents/8/"));

      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(1);
   });
});
