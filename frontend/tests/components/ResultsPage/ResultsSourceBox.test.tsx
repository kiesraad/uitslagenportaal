import { QueryClient } from "@tanstack/react-query";
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CertifiedDocument, ElectionConfig, TocEntry } from "@/api/types";
import PvPageLink from "@/components/ResultsPage/PvPageLink";
import ResultsPageColumns from "@/components/ResultsPage/ResultsPageColumns";
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

function pv(id: number, overrides: Partial<CertifiedDocument> = {}): CertifiedDocument {
   return {
      url: `/api/certified-documents/${id}/`,
      preview_url: `/api/certified-documents/${id}/preview/`,
      toc: null,
      file_type: "PDF_NA31-2",
      correction_number: null,
      ...overrides,
   };
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

function columns(documents: CertifiedDocument[], children: ReactNode = null, pvMayDiffer = false) {
   return (
      <ResultsPageColumns documents={documents} pvMayDiffer={pvMayDiffer}>
         {children}
      </ResultsPageColumns>
   );
}

const pvChoice = () => screen.queryByRole("button", { name: /Kies een proces-verbaal/ });

function pvOptions() {
   fireEvent.click(pvChoice() as HTMLElement);
   const options = screen.getAllByRole("option").map((option) => option.textContent);
   fireEvent.keyDown(screen.getByRole("listbox"), { key: "Escape" });
   return options;
}

function choosePv(name: string) {
   fireEvent.click(pvChoice() as HTMLElement);
   fireEvent.click(screen.getByRole("option", { name }));
}

function renderBox(locale: "nl" | "en" = "nl", documents: CertifiedDocument[] = []) {
   return renderWithConfig(columns(documents), locale);
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
      renderBox("nl", [pv(7)]);

      for (const image of screen.getAllByRole("img", { name: "Proces-verbaal" })) {
         expect(image).toHaveAttribute("src", "/api/certified-documents/7/preview/");
      }
      const links = screen.getAllByRole("link", { name: /proces-verbaal/i });
      expect(links).toHaveLength(2);
      for (const link of links) {
         expect(link).toHaveAttribute("href", "/api/certified-documents/7/");
         expect(link).toHaveAttribute("target", "_blank");
      }
      expect(screen.getByRole("link", { name: /Meld een fout of iets dat niet klopt/ })).toHaveAttribute(
         "href",
         "/ws2023/fout-melden",
      );
      expect(screen.getByText(/14 december om 10:00/)).toBeInTheDocument();
   });

   it("Opens the viewer from the picture and returns focus to it when closed", () => {
      renderBox("nl", [pv(7)]);

      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));

      expect(screen.getByRole("heading", { level: 2, name: "Proces-verbaal" })).toHaveFocus();
      expect(screen.queryByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).not.toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Sluiten" }));

      expect(screen.getByRole("button", { name: "Proces-verbaal" })).toHaveFocus();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });

   it("Closes the viewer when the window narrows to one column", () => {
      renderBox("nl", [pv(7)]);
      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));
      expect(screen.getByRole("button", { name: "Sluiten" })).toBeInTheDocument();

      act(() => screenWidth.narrow());

      expect(screen.queryByRole("button", { name: "Sluiten" })).not.toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Waar komen deze telresultaten vandaan?" })).toBeInTheDocument();
   });

   it("Loads the PDF only once the viewer opens, and hands it the document", async () => {
      renderBox("nl", [pv(7)]);

      // One column links to the PDF instead of opening the viewer.
      const narrowLink = screen.getByRole("link", { name: /^Proces-verbaal ?\(opent in nieuw venster\)$/ });
      expect(narrowLink).toHaveAttribute("href", "/api/certified-documents/7/");
      expect(narrowLink).toHaveAttribute("target", "_blank");
      expect(PdfDocument).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));

      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/7/?stream");
   });

   it("Says the certified election document is not published when only the document exists", () => {
      renderBox("nl", [pv(7, { preview_url: null })]);

      expect(screen.getByText(/Momenteel is het proces-verbaal nog niet gepubliceerd/)).toBeInTheDocument();
      expect(screen.queryByRole("img", { name: "Proces-verbaal" })).not.toBeInTheDocument();
      expect(screen.queryByRole("link")).not.toBeInTheDocument();
   });

   it("Says the certified election document is not published when only the preview exists", () => {
      renderBox("nl", [pv(7, { url: null })]);

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

   it("Offers no choice when the region has one PV", () => {
      renderBox("nl", [pv(7)]);

      expect(pvChoice()).not.toBeInTheDocument();
   });

   it("Lets the visitor choose a PV, the best one first, skipping one that cannot be shown", () => {
      renderBox("nl", [
         pv(9, { file_type: "PDF_NA14-2", correction_number: 2 }),
         pv(8, { file_type: "PDF_NA14-2", correction_number: 1, preview_url: null }),
         pv(7),
      ]);

      expect(pvOptions()).toEqual(["Corrigendum 2", "Proces-verbaal"]);
      expect(pvChoice()).toHaveTextContent("Corrigendum 2");
      expect(screen.getAllByRole("img", { name: "Proces-verbaal" })[0]).toHaveAttribute(
         "src",
         "/api/certified-documents/9/preview/",
      );

      choosePv("Proces-verbaal");

      expect(screen.getAllByRole("img", { name: "Proces-verbaal" })[0]).toHaveAttribute(
         "src",
         "/api/certified-documents/7/preview/",
      );
      for (const link of screen.getAllByRole("link", { name: /proces-verbaal/i })) {
         expect(link).toHaveAttribute("href", "/api/certified-documents/7/");
      }
   });

   it("Names several originals by their form", () => {
      renderBox("nl", [pv(8, { file_type: "PDF_NA31-2-B1" }), pv(7, { file_type: "PDF_N10-1" })]);

      expect(pvOptions()).toEqual([
         "Bijlage 1 bij proces-verbaal gemeentelijk stembureau (CSO)",
         "Proces-verbaal stembureau",
      ]);
   });

   it("Switches the open viewer to the chosen PV at page 1 when it lacks the section shown", async () => {
      renderBox("nl", [pv(9, { file_type: "PDF_NA14-2", correction_number: 1 }), pv(7)]);
      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));
      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      act(() => PdfDocument.mock.lastCall?.[0].onPageChange(4));

      choosePv("Proces-verbaal");

      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/7/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(1);
   });

   it("Keeps the section shown when switching to a PV that has it", async () => {
      renderBox("nl", [
         pv(9, {
            file_type: "PDF_NA14-2",
            correction_number: 1,
            toc: [
               { page: 2, content: "candidate-votes", list_number: 5 },
               { page: 3, content: "candidate-votes-continued", list_number: 5 },
            ],
         }),
         pv(7, {
            toc: [
               { page: 6, content: "candidate-votes", list_number: 4 },
               { page: 8, content: "candidate-votes", list_number: 5 },
            ],
         }),
      ]);
      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));
      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      act(() => PdfDocument.mock.lastCall?.[0].onPageChange(3));

      // A continued page of list 5 opens the original at list 5.
      choosePv("Proces-verbaal");
      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/7/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(8);

      choosePv("Corrigendum 1");
      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/9/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(2);
   });

   it("Warns the PV may differ from the counts, in the box and in the viewer", () => {
      renderWithConfig(columns([pv(7)], null, true));

      expect(screen.getByText(/De aantallen in het proces-verbaal kunnen daardoor afwijken/)).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Proces-verbaal" }));

      expect(screen.getByText(/De aantallen in het proces-verbaal kunnen daardoor afwijken/)).toBeInTheDocument();
   });

   it("Does not warn when nothing was corrected, or when there is no PV", () => {
      const { unmount } = renderWithConfig(columns([pv(7)]));
      expect(screen.queryByText(/kunnen daardoor afwijken/)).not.toBeInTheDocument();
      unmount();

      renderWithConfig(columns([], null, true));
      expect(screen.queryByText(/kunnen daardoor afwijken/)).not.toBeInTheDocument();
   });
});

describe("PvPageLink", () => {
   const toc: TocEntry[] = [
      { page: 1, content: "cover" },
      { page: 3, content: "admitted-voters" },
   ];

   beforeEach(() => {
      PdfDocument.mockClear();
      screenWidth.matches = true;
   });

   it("Links to the first candidate page of the given list only", () => {
      const listToc: TocEntry[] = [
         { page: 5, content: "candidate-votes", list_number: 1 },
         { page: 6, content: "candidate-votes", list_number: 2 },
         { page: 7, content: "candidate-votes-continued", list_number: 2 },
      ];
      renderWithConfig(
         columns(
            [pv(7, { toc: listToc })],
            <>
               <PvPageLink content="candidate-votes" listNumber={2} />
               <PvPageLink content="candidate-votes" listNumber={3} />
            </>,
         ),
      );

      const links = screen.getAllByRole("link", { name: /Toon in proces-verbaal/ });
      expect(links).toHaveLength(1);
      expect(links[0]).toHaveAttribute("href", "/api/certified-documents/7/#page=6");
   });

   it("Shows no link while the page is unknown", () => {
      renderWithConfig(columns([pv(7)], <PvPageLink content="admitted-voters" />));

      expect(screen.queryByText("Toon in proces-verbaal")).not.toBeInTheDocument();
   });

   it("Opens the viewer at the page, and jumps there when it is open", async () => {
      renderWithConfig(columns([pv(7, { toc })], <PvPageLink content="admitted-voters" />));

      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3);

      act(() => PdfDocument.mock.lastCall?.[0].onPageChange(1));
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(1);

      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3);
   });

   it("Opens the PDF at the page in a new tab on one column", () => {
      renderWithConfig(columns([pv(7, { toc })], <PvPageLink content="admitted-voters" />));

      const link = screen.getByRole("link", { name: /Toon in proces-verbaal/ });
      expect(link).toHaveAttribute("href", "/api/certified-documents/7/#page=3");
      expect(link).toHaveAttribute("target", "_blank");
   });

   it("Starts at page 1 when the viewer shows another region's document", async () => {
      const { rerender } = renderWithConfig(columns([pv(7, { toc })], <PvPageLink content="admitted-voters" />));
      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      await waitFor(() => expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(3));

      rerender(columns([pv(8, { toc })], <PvPageLink content="admitted-voters" />));

      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/8/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(1);
   });

   it("Keeps a link the chosen PV lacks, and opens the PV that has the page with a note", async () => {
      const correctionToc: TocEntry[] = [{ page: 2, content: "candidate-votes", list_number: 3 }];
      const originalToc: TocEntry[] = [
         { page: 5, content: "candidate-votes", list_number: 3 },
         { page: 8, content: "candidate-votes", list_number: 5 },
      ];
      renderWithConfig(
         columns(
            [pv(9, { file_type: "PDF_NA14-2", correction_number: 1, toc: correctionToc }), pv(7, { toc: originalToc })],
            <>
               <PvPageLink content="candidate-votes" listNumber={3} />
               <PvPageLink content="candidate-votes" listNumber={5} />
            </>,
         ),
      );

      const [list3, list5] = screen.getAllByRole("button", { name: "Toon in proces-verbaal" });
      // List 3 is in the corrigendum, which is chosen; list 5 only in the original.
      expect(
         screen.getAllByRole("link", { name: /Toon in proces-verbaal/ }).map((link) => link.getAttribute("href")),
      ).toEqual(["/api/certified-documents/9/#page=2", "/api/certified-documents/7/#page=8"]);

      fireEvent.click(list5);
      await waitFor(() => expect(PdfDocument).toHaveBeenCalled());
      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/7/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(8);
      expect(pvChoice()).toHaveTextContent("Proces-verbaal");
      expect(
         screen.getByText("Getoond: Proces-verbaal. Dit onderdeel staat niet in Corrigendum 1."),
      ).toBeInTheDocument();

      // The original has list 3 as well, so the viewer stays on it, without the note.
      fireEvent.click(list3);
      expect(PdfDocument.mock.lastCall?.[0].file).toBe("/api/certified-documents/7/?stream");
      expect(PdfDocument.mock.lastCall?.[0].pageNumber).toBe(5);
      expect(screen.queryByText(/Getoond:/)).not.toBeInTheDocument();
      // Both links are still there.
      expect(screen.getAllByRole("button", { name: "Toon in proces-verbaal" })).toHaveLength(2);
   });

   it("Drops the note once the visitor chooses a PV", async () => {
      renderWithConfig(
         columns(
            [pv(9, { file_type: "PDF_NA14-2", correction_number: 1 }), pv(7, { toc })],
            <PvPageLink content="admitted-voters" />,
         ),
      );
      fireEvent.click(screen.getByRole("button", { name: "Toon in proces-verbaal" }));
      await waitFor(() => expect(screen.getByText(/Getoond:/)).toBeInTheDocument());

      choosePv("Corrigendum 1");

      expect(screen.queryByText(/Getoond:/)).not.toBeInTheDocument();
   });
});
