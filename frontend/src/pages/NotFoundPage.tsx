import { Trans, useLingui } from "@lingui/react/macro";
import { Link } from "react-router";
import { LayoutMain } from "../components/LayoutMain.tsx";
import PageTop from "../components/PageTop.tsx";
import { appRoutes } from "../utils/routes.ts";

export function NotFoundPage() {
   const { t } = useLingui();
   const title = t`Pagina niet gevonden`;

   return (
      <LayoutMain title={title}>
         <div className="not-found-top">
            <PageTop title={title} />
         </div>
         <div className="page-main">
            <div className="page-space-2 max-w-2xl">
               <p className="text-lg">
                  <Trans>De pagina die u wilde zien of het bestand dat u wilde bekijken is niet gevonden.</Trans>
               </p>

               <section className="flex flex-col gap-3">
                  <h2>
                     <Trans>U kunt de informatie die u zoekt mogelijk vinden via de volgende pagina's:</Trans>
                  </h2>
                  <ul className="flex flex-col gap-2 list-none p-0 m-0">
                     <li className="flex items-center gap-2">
                        <span className="not-found-chevron">›</span>
                        <Link to={appRoutes.home()}>
                           <Trans>Homepage</Trans>
                        </Link>
                     </li>
                  </ul>
               </section>
            </div>
         </div>
      </LayoutMain>
   );
}
