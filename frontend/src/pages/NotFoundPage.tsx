import { Trans, useLingui } from "@lingui/react/macro";
import { data, Link } from "react-router";
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
            <div className="flex max-w-2xl flex-col gap-8">
               <p className="text-lg">
                  <Trans>De pagina die u wilde zien of het bestand dat u wilde bekijken is niet gevonden.</Trans>
               </p>

               <section className="flex flex-col gap-3">
                  <h2>
                     <Trans>U kunt de informatie die u zoekt mogelijk vinden via de volgende pagina's:</Trans>
                  </h2>
                  <ul className="m-0 flex list-none flex-col gap-2 p-0">
                     <li className="flex items-center gap-2">
                        <span className="not-found-chevron" aria-hidden="true">
                           ›
                        </span>
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

// An unknown URL answers 404, so the error boundary shows this page with the right status.
export function loader(): never {
   throw data(null, { status: 404 });
}
export const clientLoader = loader;

// The default export makes this module a route module rather than a resource route.
export default NotFoundPage;
