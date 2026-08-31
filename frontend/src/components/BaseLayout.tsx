import type { ReactNode } from "react";
import { Footer } from "./Footer";
import { Header } from "./Header";

export function BaseLayout({ children }: { children: ReactNode }) {
   return (
      <>
         <Header />
         {children}
         <Footer />
      </>
   );
}
