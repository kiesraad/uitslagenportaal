import { faHourglass } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { ElectionTimelineSection } from "@/components/Timeline/ElectionTimelineSection.tsx";
import PageSection from "@/elements/PageSection.tsx";
import { HeroGrid } from "../components/HomePage/HeroGrid.tsx";
import { LayoutMain } from "../components/LayoutMain.tsx";
import { electionConfigsQuery } from "../hooks/queries.ts";
import { appRoutes } from "../utils/routes.ts";

export async function loadHome(client: QueryClient) {
   await client.query(electionConfigsQuery());
}

export default function HomePage() {
   const { t } = useLingui();
   const { data: election_configs } = useSuspenseQuery(electionConfigsQuery());
   const hasResult = election_configs.length > 0;

   return (
      <LayoutMain title={t`Home`} description={t`De telresultaten van alle stembureaus in Nederland.`}>
         <PageSection className="relative grid flex-1 grid-cols-1 overflow-hidden bg-blue-100 lg:grid-cols-2 lg:gap-20">
            <div className="flex flex-col justify-center gap-3.5 sm:gap-6.5">
               <h1 className="font-title max-w-xl text-3xl font-bold sm:text-4xl">
                  <Trans>De telresultaten van alle stembureaus in Nederland.</Trans>
               </h1>
               <p>
                  <Trans>
                     Op deze website publiceert de Kiesraad de telresultaten van alle gemeenten en stembureaus. Je vindt
                     hier ook de brondocumenten waarin stembureaus hun tellingen hebben opgeschreven. Zo kan iedereen
                     controleren of de stemmen goed zijn geteld en in de definitieve uitslag terecht zijn gekomen.
                  </Trans>
               </p>

               {hasResult ? (
                  <div className={"home-hero-card"}>
                     <h2>
                        <Trans>Bekijk de telresultaten</Trans>
                     </h2>
                     {election_configs.map((election_config) => (
                        <div key={election_config.slug} className={"home-hero-card-link"}>
                           <span className="gemeente-chevron mb-1" aria-hidden="true">
                              ›
                           </span>
                           <Link
                              to={appRoutes.electionConfigMunicipalityList(election_config.slug)}
                              className="font-semibold"
                           >
                              {election_config.label}
                           </Link>
                        </div>
                     ))}
                  </div>
               ) : (
                  <div className={"home-hero-card"}>
                     <div className="flex items-center gap-2">
                        <FontAwesomeIcon icon={faHourglass} />
                        <h2>
                           <Trans>Telresultaten volgen binnenkort</Trans>
                        </h2>
                     </div>
                     <p>
                        <Trans>
                           Op dit moment zijn er nog geen telresultaten van een verkiezing beschikbaar. Wanneer de dag
                           van stemming nadert, zal een verkiezing met bijbehorende regio's worden aangemaakt. Vanaf de
                           dag van stemming zullen via deze pagina de tellingen worden weergegeven. Na 3 maanden worden
                           de resultaten weer verwijderd.
                        </Trans>
                     </p>
                  </div>
               )}
            </div>

            <HeroGrid />
         </PageSection>

         {election_configs.length === 1 && <ElectionTimelineSection electionConfig={election_configs[0]} />}
      </LayoutMain>
   );
}
