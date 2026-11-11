import { I18nProvider } from "@lingui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { createRoutesStub, Link, Outlet } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { RouteFocus } from "@/components/RouteFocus";
import ErrorBoundaryPage from "@/pages/ErrorBoundaryPage";
import { activateLocale } from "../testUtils";

function Empty() {
   return null;
}

/** Mounts the boundary the way the root route does: as the catcher for a failing loader. */
function renderThrownError(error: unknown) {
   const i18n = activateLocale("nl");

   const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
   const Stub = createRoutesStub([
      {
         id: "root",
         path: "*",
         loader: () => {
            throw error;
         },
         HydrateFallback: Empty,
         Component: Empty,
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

// Mirrors root.tsx: React Router renders `Layout` separately around the root component and around
// the root error boundary, so it remounts when one replaces the other. The real `Layout` renders
// `<html>`, so it cannot be mounted here.
function Layout({ children }: { children: ReactNode }) {
   return (
      <>
         <RouteFocus />
         <Link to="/">Naar home</Link>
         {children}
      </>
   );
}

function RootComponent() {
   return (
      <Layout>
         <Outlet />
      </Layout>
   );
}

function RootErrorBoundary() {
   return (
      <Layout>
         <ErrorBoundaryPage />
      </Layout>
   );
}

function HomeRoute() {
   return (
      <main>
         <h1>Home</h1>
         <Link to="/missing">Naar ontbrekend</Link>
         <Link to="/broken">Naar kapot</Link>
      </main>
   );
}

function throwingRoute(path: string, error: unknown) {
   return {
      path,
      loader: () => {
         throw error;
      },
      Component: Empty,
   };
}

function renderNavigableApp() {
   const i18n = activateLocale("nl");
   const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
   const Stub = createRoutesStub([
      {
         path: "/",
         Component: RootComponent,
         ErrorBoundary: RootErrorBoundary,
         children: [
            { index: true, Component: HomeRoute },
            throwingRoute("missing", new ApiError("Request failed: Not Found", 404)),
            throwingRoute("broken", new Error("kapot")),
         ],
      },
   ]);

   return render(
      <I18nProvider i18n={i18n}>
         <QueryClientProvider client={queryClient}>
            <Stub initialEntries={["/"]} />
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

   it("Announces the failure as an alert, apart from the heading", async () => {
      renderThrownError(new ApiError("Request failed: Server Error", 500));

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent("Er is een fout opgetreden");
      expect(alert).not.toContainElement(screen.getByRole("heading", { level: 1, name: "Fout" }));
   });

   it("Has no alert on the not-found page", async () => {
      renderThrownError(new ApiError("Request failed: Not Found", 404));

      await screen.findByRole("heading", { name: "Pagina niet gevonden" });
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
   });

   describe("focus", () => {
      it("Leaves focus alone on the first render", () => {
         renderNavigableApp();

         expect(document.activeElement).toBe(document.body);
      });

      it("Focuses the h1 when navigating into the not-found page", async () => {
         renderNavigableApp();

         fireEvent.click(screen.getByRole("link", { name: "Naar ontbrekend" }));

         const heading = await screen.findByRole("heading", { level: 1, name: "Pagina niet gevonden" });
         // Focus is set in a passive effect, which can land just after the heading appears.
         await waitFor(() => expect(heading).toHaveFocus());
      });

      it("Focuses the h1 when navigating into the error page", async () => {
         renderNavigableApp();

         fireEvent.click(screen.getByRole("link", { name: "Naar kapot" }));

         const heading = await screen.findByRole("heading", { level: 1, name: "Fout" });
         // Focus is set in a passive effect, which can land just after the heading appears.
         await waitFor(() => expect(heading).toHaveFocus());
      });

      it("Focuses the h1 again when navigating back out of the boundary", async () => {
         renderNavigableApp();
         fireEvent.click(screen.getByRole("link", { name: "Naar kapot" }));
         await screen.findByRole("heading", { level: 1, name: "Fout" });

         fireEvent.click(screen.getByRole("link", { name: "Naar home" }));

         const heading = await screen.findByRole("heading", { level: 1, name: "Home" });
         // Focus is set in a passive effect, which can land just after the heading appears.
         await waitFor(() => expect(heading).toHaveFocus());
      });
   });
});
