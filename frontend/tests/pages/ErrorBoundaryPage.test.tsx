import { i18n } from "@lingui/core";
import { I18nProvider } from "@lingui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createRoutesStub } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage";
import { activateLocale } from "../testUtils";

/** Mounts the boundary the way the root route does: as the catcher for a failing loader. */
function renderThrownError(error: unknown) {
   activateLocale("nl");

   const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
   const Stub = createRoutesStub([
      {
         id: "root",
         path: "*",
         loader: () => {
            throw error;
         },
         HydrateFallback: () => null,
         Component: () => null,
         ErrorBoundary: ErrorBoundaryPage,
      },
   ]);

   return render(
      <I18nProvider i18n={i18n}>
         <QueryClientProvider client={queryClient}>
            <Stub />
         </QueryClientProvider>
      </I18nProvider>,
   );
}

beforeEach(() => {
   // The boundary renders the chrome, whose footer queries the elections.
   vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve([]) } as Response)),
   );
});

afterEach(() => {
   vi.unstubAllGlobals();
});

describe("ErrorBoundaryPage", () => {
   it("Shows the not-found page when a loader 404s", async () => {
      renderThrownError(new ApiError("Request failed: Not Found", 404));

      expect(await screen.findByRole("heading", { name: "Pagina niet gevonden" })).toBeInTheDocument();
   });

   it("Reports any other failure with its status and message", async () => {
      renderThrownError(new ApiError("Request failed: Server Error", 500));

      expect(await screen.findByRole("heading", { name: "Fout" })).toBeInTheDocument();
      expect(screen.getByText(/500 - Request failed: Server Error/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Probeer opnieuw/ })).toBeInTheDocument();
   });
});
