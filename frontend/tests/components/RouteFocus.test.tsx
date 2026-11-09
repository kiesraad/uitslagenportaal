import { fireEvent, render, screen } from "@testing-library/react";
import { createRoutesStub, Link, Outlet } from "react-router";
import { describe, expect, it } from "vitest";
import { RouteFocus } from "@/components/RouteFocus";

// RouteFocus sits in a layout route, as in the app's `App` in root.tsx, so it stays mounted across navigations.
function Layout() {
   return (
      <>
         <RouteFocus />
         <main>
            <Outlet />
         </main>
      </>
   );
}

function HomeRoute() {
   return (
      <>
         <h1>Home</h1>
         <Link to="/gemeente">Naar gemeente</Link>
         <Link to="/#uitleg">Naar uitleg</Link>
      </>
   );
}

function GemeenteRoute() {
   return <h1>Gemeente</h1>;
}

function renderRoutes() {
   const Stub = createRoutesStub([
      {
         path: "/",
         Component: Layout,
         children: [
            { index: true, Component: HomeRoute },
            { path: "gemeente", Component: GemeenteRoute },
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
