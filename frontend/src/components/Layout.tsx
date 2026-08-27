import type { ReactNode } from "react";
import HtmlHead from "@/components/HtmlHead.tsx";
import { Footer } from "./Footer";
import { Header } from "./Header";

interface LayoutProps {
   children: ReactNode;
   title?: string;
   description?: string;
}

export function Layout({ children, title, description }: LayoutProps) {
   return (
      <>
         <HtmlHead title={title} description={description} />
         <Header />
         <main className="layout-main">{children}</main>
         <Footer />
      </>
   );
}
