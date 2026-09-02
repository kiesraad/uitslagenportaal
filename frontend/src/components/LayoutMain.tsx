import type { ReactNode } from "react";
import HtmlHead from "@/components/HtmlHead.tsx";

interface LayoutMainProps {
   children: ReactNode;
   title?: string;
   description?: string;
}

export function LayoutMain({ children, title, description }: LayoutMainProps) {
   return (
      <>
         <HtmlHead title={title} description={description} />
         <main className="layout-main">{children}</main>
      </>
   );
}
