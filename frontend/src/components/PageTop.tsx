import type { ReactNode } from "react";
import { BreadcrumbItem, Breadcrumbs } from "@/components/Breadcrumbs.tsx";

type Props = {
   title: string;
   subtitle?: string;
   breadcrumb?: ({
      href?: string;
      label: string;
   } | null)[];
   tabs?: ReactNode;
};

export default function PageTop({ title, subtitle, breadcrumb, tabs }: Props) {
   // entries may be null when a crumb does not apply, e.g. a region without a CSB
   const breadcrumbItems = breadcrumb?.filter((item) => item !== null);

   return (
      <div className="page-top">
         {breadcrumbItems && (
            <Breadcrumbs>
               {breadcrumbItems.map((item) => (
                  <BreadcrumbItem key={`${item.href}-${item.label}`} to={item.href}>
                     {item.label}
                  </BreadcrumbItem>
               ))}
            </Breadcrumbs>
         )}

         <div className="pb-12">
            <h1 className="font-title mb-3 text-3xl font-bold wrap-break-word hyphens-auto sm:text-4xl sm:whitespace-pre-line">
               {title}
            </h1>
            {subtitle && <p>{subtitle}</p>}
         </div>

         {tabs || null}
      </div>
   );
}
