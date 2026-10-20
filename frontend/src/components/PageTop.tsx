import type { ReactNode } from "react";
import { BreadcrumbItem, Breadcrumbs } from "@/components/Breadcrumbs.tsx";
import { InfoBox } from "@/components/InfoBox.tsx";

type Props = {
   title: string;
   subtitle?: string;
   breadcrumb?: ({
      href?: string;
      label: string;
   } | null)[];
   notice?: ReactNode;
   tabs?: ReactNode;
};

export default function PageTop({ title, subtitle, breadcrumb, notice, tabs }: Props) {
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

         <div className="flex flex-col gap-6 pb-12 lg:flex-row lg:items-start">
            <div>
               <h1 className="mb-3 hyphens-auto font-bold font-title text-3xl sm:whitespace-pre-line sm:text-4xl">
                  {title}
               </h1>
               {subtitle && <p>{subtitle}</p>}
            </div>
            {notice && (
               <InfoBox disableMargin className="bg-white! lg:max-w-sm">
                  <p>{notice}</p>
               </InfoBox>
            )}
         </div>

         {tabs || null}
      </div>
   );
}
