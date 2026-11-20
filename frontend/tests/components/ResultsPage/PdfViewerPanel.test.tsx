import { act, fireEvent, screen } from "@testing-library/react";
import { type ReactNode, useState } from "react";
import { describe, expect, it, vi } from "vitest";
import PdfViewerPanel from "@/components/ResultsPage/PdfViewerPanel";
import { renderWithProviders } from "../../testUtils";

// PDF.js needs a canvas and a worker, which jsdom does not have. `pdf.load()` finishes loading a three-page PDF.
const pdf = vi.hoisted(() => ({ load: () => {} }));
vi.mock("react-pdf", () => ({
   pdfjs: { GlobalWorkerOptions: {} },
   Document: ({
      onLoadSuccess,
      children,
   }: {
      onLoadSuccess: (document: { numPages: number }) => void;
      children: ReactNode;
   }) => {
      pdf.load = () => onLoadSuccess({ numPages: 3 });
      return children;
   },
   Page: () => null,
}));

// jsdom has no ResizeObserver.
vi.stubGlobal(
   "ResizeObserver",
   class {
      observe() {}
      disconnect() {}
   },
);

const documentUrl = "/api/certified-documents/7/";

function StatefulPanel({ url }: { url: string }) {
   const [page, setPage] = useState(1);
   return <PdfViewerPanel documentUrl={url} pageNumber={page} onPageChange={setPage} onClose={() => {}} />;
}

function panel(url = documentUrl) {
   return <StatefulPanel url={url} />;
}

async function renderLoadedPanel() {
   const view = renderWithProviders(panel());
   await screen.findByRole("region", { name: "Proces-verbaal" });
   act(() => pdf.load());
   return view;
}

describe("PdfViewerPanel", () => {
   it("Disables both page buttons until the PDF has loaded", async () => {
      renderWithProviders(panel());

      expect(await screen.findByRole("button", { name: "Vorige pagina" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Volgende pagina" })).toBeDisabled();
      expect(screen.queryByText(/Pagina \d van/)).not.toBeInTheDocument();
   });

   it("Pages through the PDF and disables the buttons at either end", async () => {
      await renderLoadedPanel();
      const previous = screen.getByRole("button", { name: "Vorige pagina" });
      const next = screen.getByRole("button", { name: "Volgende pagina" });

      expect(screen.getByText("Pagina 1 van 3")).toBeInTheDocument();
      expect(previous).toBeDisabled();
      expect(next).toBeEnabled();

      fireEvent.click(next);
      expect(screen.getByText("Pagina 2 van 3")).toBeInTheDocument();
      expect(previous).toBeEnabled();

      fireEvent.click(next);
      expect(screen.getByText("Pagina 3 van 3")).toBeInTheDocument();
      expect(next).toBeDisabled();

      fireEvent.click(previous);
      expect(screen.getByText("Pagina 2 van 3")).toBeInTheDocument();
   });

   it("Moves focus to the other page button when one becomes disabled", async () => {
      await renderLoadedPanel();
      const previous = screen.getByRole("button", { name: "Vorige pagina" });
      const next = screen.getByRole("button", { name: "Volgende pagina" });

      fireEvent.click(next);
      fireEvent.click(next);
      expect(previous).toHaveFocus();

      fireEvent.click(previous);
      fireEvent.click(previous);
      expect(next).toHaveFocus();
   });

   it("Shows each new page from the top", async () => {
      await renderLoadedPanel();
      const page = screen.getByRole("region", { name: "Proces-verbaal" });
      page.scrollTop = 200;

      fireEvent.click(screen.getByRole("button", { name: "Volgende pagina" }));

      expect(page.scrollTop).toBe(0);
   });

   it("Links to the PDF in a new tab", async () => {
      renderWithProviders(panel());

      const link = await screen.findByRole("link", { name: /Bekijk het proces-verbaal/ });
      expect(link).toHaveAttribute("href", documentUrl);
      expect(link).toHaveAttribute("target", "_blank");
   });
});
