import { useLocation, useRouteLoaderData } from "react-router";
import type { clientLoader } from "@/root.tsx";

interface HtmlHeadProps {
   title?: string;
   description?: string;
}

export default function HtmlHead({ title, description }: HtmlHeadProps) {
   const pageTitle = [title || "", "Kiesraad"].join(" - ");
   const pageDescription = description || title;
   const origin = useRouteLoaderData<typeof clientLoader>("root")?.origin;
   const { pathname } = useLocation();
   const url = origin && `${origin}${pathname}`;
   return (
      <>
         <title>{pageTitle}</title>
         <meta name="description" content={pageDescription} />
         <meta property="og:title" content={pageTitle} />
         <meta property="og:description" content={pageDescription} />
         {url && <link rel="canonical" href={url} />}
         {url && <meta property="og:url" content={url} />}
         {origin && <meta property="og:image" content={`${origin}/images/share.png`} />}
      </>
   );
}
