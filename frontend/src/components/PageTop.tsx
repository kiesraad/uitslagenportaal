import type { ReactNode } from "react";
import { Link } from "react-router";

type Props = {
   title: string;
   subtitle?: string;
   breadcrumb?: ({
      href: string;
      label: string;
   } | null)[];
   tabs?: ReactNode;
};

export default function PageTop({ title, subtitle, breadcrumb, tabs }: Props) {
   // entries may be null when a crumb does not apply, e.g. a region without a CSB
   const breadcrumbItems = breadcrumb?.filter((item) => item !== null);

   return (
      <div className="page-top">
         {breadcrumbItems ? (
            <nav className="breadcrumb" aria-label="Breadcrumb">
               {breadcrumbItems.map((item, index) => (
                  <span key={`${item.href}-${item.label}`} className="breadcrumb-item">
                     <Link to={item.href}>{item.label}</Link>
                     {index < breadcrumbItems.length - 1 && <span className="breadcrumb-sep">{">"}</span>}
                  </span>
               ))}
            </nav>
         ) : null}

         <div className="pb-12">
            <h1 className="mb-3 text-3xl sm:text-4xl font-title font-bold whitespace-pre-line">{title}</h1>
            {subtitle && <p>{subtitle}</p>}
         </div>

         {tabs || null}
      </div>
   );
}
