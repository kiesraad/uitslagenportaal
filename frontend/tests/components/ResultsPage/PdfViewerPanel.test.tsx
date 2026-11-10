import { act, fireEvent, screen } from "@testing-library/react";
import type { ReactNode } from "react";
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

function panel(url = documentUrl) {
   return <PdfViewerPanel documentUrl={url} onClose={() => {}} />;
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

   it("Shows each new page from the top", async () => {
      await renderLoadedPanel();
      const page = screen.getByRole("region", { name: "Proces-verbaal" });
      page.scrollTop = 200;

      fireEvent.click(screen.getByRole("button", { name: "Volgende pagina" }));

      expect(page.scrollTop).toBe(0);
   });

   it("Starts at page 1 again when it shows another document", async () => {
      const { rerender } = await renderLoadedPanel();
      fireEvent.click(screen.getByRole("button", { name: "Volgende pagina" }));
      expect(screen.getByText("Pagina 2 van 3")).toBeInTheDocument();

      rerender(panel("/api/certified-documents/8/"));
      act(() => pdf.load());

      expect(screen.getByText("Pagina 1 van 3")).toBeInTheDocument();
   });

   it("Links to the PDF in a new tab", async () => {
      renderWithProviders(panel());

      const link = await screen.findByRole("link", { name: /Bekijk het proces-verbaal/ });
      expect(link).toHaveAttribute("href", documentUrl);
      expect(link).toHaveAttribute("target", "_blank");
   });
});
