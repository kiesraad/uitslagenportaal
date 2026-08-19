import type { ReactNode } from "react";

type Props = {
   links: {
      label: ReactNode;
      url: string;
   }[];
};

export default function PageIndex({ links }: Props) {
   return (
      <div className="on-this-page">
         <div className="on-this-page-title">Op deze pagina:</div>
         <ul>
            {links.map((link) => (
               <li key={link.url}>
                  <a href={link.url} className="on-this-page-link">
                     {link.label}
                  </a>
               </li>
            ))}
         </ul>
      </div>
   );
}
