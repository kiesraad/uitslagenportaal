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
         {/* Without a title the page renders its own HtmlHead; a second <title> would be empty. */}
         {title && <HtmlHead title={title} description={description} />}
         {/* Focusable as the skip link's target. */}
         <main id="main-content" tabIndex={-1} className="flex w-full flex-1 flex-col focus:outline-none">
            {children}
         </main>
      </>
   );
}
