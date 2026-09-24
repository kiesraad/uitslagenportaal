import { fireEvent, render, screen } from "@testing-library/react";
import { createRoutesStub, Link, Outlet } from "react-router";
import { describe, expect, it } from "vitest";
import { RouteFocus } from "@/components/RouteFocus";

// RouteFocus sits in a layout route, as in the app's RootLayout, so it stays mounted across navigations.
function renderRoutes() {
   const Stub = createRoutesStub([
      {
         path: "/",
         Component: () => (
            <>
               <RouteFocus />
               <main>
                  <Outlet />
               </main>
            </>
         ),
         children: [
            {
               index: true,
               Component: () => (
                  <>
                     <h1>Home</h1>
                     <Link to="/gemeente">Naar gemeente</Link>
                     <Link to="/#uitleg">Naar uitleg</Link>
                  </>
               ),
            },
            { path: "gemeente", Component: () => <h1>Gemeente</h1> },
         ],
      },
   ]);

   render(<Stub initialEntries={["/"]} />);
}

describe("RouteFocus", () => {
   it("leaves focus alone on the first page load", () => {
      renderRoutes();

      expect(document.activeElement).toBe(document.body);
   });

   it("focuses the new page's h1 after navigating", async () => {
      renderRoutes();

      fireEvent.click(screen.getByRole("link", { name: "Naar gemeente" }));

      const heading = await screen.findByRole("heading", { level: 1, name: "Gemeente" });
      expect(heading).toHaveFocus();
   });

   it("keeps focus in place when only the hash changes", () => {
      renderRoutes();
      const link = screen.getByRole("link", { name: "Naar uitleg" });
      link.focus();

      fireEvent.click(link);

      expect(link).toHaveFocus();
   });
});
