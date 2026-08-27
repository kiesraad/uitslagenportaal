import type { ReactNode } from "react";
import { Footer } from "./Footer";
import { Header } from "./Header";

/**
 * The persistent chrome. It lives above the router Outlet so that it — and the
 * navigation progress bar inside the header — stays mounted while pages swap.
 */
export function BaseLayout({ children }: { children: ReactNode }) {
   return (
      <>
         <Header />
         {children}
         <Footer />
      </>
   );
}
