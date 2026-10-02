import { Trans } from "@lingui/react/macro";
import type { ReactNode } from "react";
import { Link } from "react-router";

type Props = {
   links: {
      label: ReactNode;
      url: string;
   }[];
};

export default function PageIndex({ links }: Props) {
   return (
      <div className="on-this-page">
         <div className="on-this-page-title">
            <Trans>Op deze pagina:</Trans>
         </div>
         <ul>
            {links.map((link) => (
               <li key={link.url}>
                  <Link to={{ hash: link.url }} className="on-this-page-link" replace>
                     {link.label}
                  </Link>
               </li>
            ))}
         </ul>
      </div>
   );
}
