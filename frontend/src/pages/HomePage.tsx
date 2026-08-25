import { faHourglass } from "@fortawesome/free-regular-svg-icons";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { Link } from "react-router";
import type { ElectionConfig } from "../api/types.ts";
import { HeroGrid } from "../components/HomePage/HeroGrid.tsx";
import { Layout } from "../components/Layout.tsx";
import Timeline, { type TimelineEntry } from "../components/Timeline.tsx";
import { useElectionConfigs } from "../hooks/queries.ts";
import { appRoutes } from "../utils/routes.ts";

export function HomePage() {
   const { t } = useLingui();
   const { data, isLoading, isError, refetch } = useElectionConfigs();
   const election_configs: ElectionConfig[] = data ?? [];
   const hasResult = election_configs.length > 0;

   // If there is only one election and it has timeline entries, build the timeline
   let timelineEntries: TimelineEntry[] = [];
   if (election_configs.length === 1 && election_configs[0]?.timeline_entries?.length) {
      timelineEntries = election_configs[0].timeline_entries
         .slice()
         .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
         .map((entry) => ({
            status: entry.status,
            title: entry.title,
            date: entry.date,
            body: entry.body,
         }));
   }

   return (
      <Layout title={t`Home`} description={t`De telresultaten van alle stembureaus in Nederland.`}>
         <section className={"page-top home-page-hero"}>
            <div className={"home-page-hero-left"}>
               <h1 className="text-3xl sm:text-4xl font-title font-bold">
                  <Trans>
                     De telresultaten van alle <br /> stembureaus in Nederland.
                  </Trans>
               </h1>
               <p>
                  <Trans>
                     Op deze website publiceert de Kiesraad de telresultaten van alle gemeenten en stembureaus. Je vindt
                     hier ook de brondocumenten waarin stembureaus hun tellingen hebben opgeschreven. Zo kan iedereen
                     controleren of de stemmen goed zijn geteld en in de definitieve uitslag terecht zijn gekomen.
                  </Trans>
               </p>

               {isLoading ? (
                  <div className={"home-hero-card"}>
                     <h2>
                        <Trans>Bekijk de telresultaten</Trans>
                     </h2>
                     <p>
                        <Trans>Verkiezingen laden…</Trans>
                     </p>
                  </div>
               ) : isError ? (
                  <div className={"home-hero-card"}>
                     <h2>
                        <Trans>Bekijk de telresultaten</Trans>
                     </h2>
                     <p>
                        <Trans>Kan verkiezingen niet laden.</Trans>
                     </p>
                     <button type="button" onClick={() => refetch()}>
                        <Trans>Opnieuw proberen</Trans>
                     </button>
                  </div>
               ) : hasResult ? (
                  <div className={"home-hero-card"}>
                     <h2>
                        <Trans>Bekijk de telresultaten</Trans>
                     </h2>
                     {election_configs.map((election_config) => (
                        <div key={election_config.slug} className={"home-hero-card-link"}>
                           <span className="gemeente-chevron mb-1">›</span>
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
                     <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
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
         </section>

         {election_configs.length === 1 && (
            <>
               <section className="page-main page-main-w-half">
                  <h2 className="home-process-title">
                     <Trans>Hoe komt de uitslag tot stand?</Trans>
                  </h2>
                  <p className="home-process-intro">
                     <Trans>
                        Hieronder wordt stap voor stap uitgelegd hoe het resultaat van de verkiezing tot stand komt. Het
                        begint bij het stembureau en eindigt bij de definitieve uitslag die de Kiesraad publiceert. Bij
                        iedere stap is er controle, zodat de uitslag klopt.
                     </Trans>
                  </p>

                  <Timeline entries={timelineEntries} />
               </section>

               <section className="home-bottom-info page-main-w-half">
                  <div className="home-info-box">
                     <div className="home-info-body">
                        <h3>
                           <Trans>Benieuwd naar de resultaten in het stembureau waar u gestemd heeft?</Trans>
                        </h3>
                        {election_configs.map((election_config) => {
                           const electionLabel = election_config.label;
                           return (
                              <div key={election_config.slug} className={"home-hero-card-link"}>
                                 <span className="gemeente-chevron">›</span>
                                 <Link to={appRoutes.electionConfigMunicipalityList(election_config.slug)}>
                                    <Trans>Bekijk de tellingen per stembureau voor {electionLabel}</Trans>
                                 </Link>
                              </div>
                           );
                        })}
                     </div>
                  </div>

                  <div className="home-external-links">
                     <p>
                        <Trans>
                           Deze website is actief vanaf 1 dag vóór de verkiezingen tot drie maanden erna. Wilt u
                           uitslagen van eerdere verkiezingen bekijken?
                        </Trans>{" "}
                        <br />
                        <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                           <Trans>Ga dan naar</Trans>{" "}
                           <a
                              style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}
                              href="https://www.verkiezingsuitslagen.nl/"
                              target="_blank"
                              rel="noopener noreferrer"
                           >
                              <Trans>Databank verkiezinguitslag</Trans>
                              <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                           </a>
                        </span>
                     </p>
                  </div>
               </section>
            </>
         )}
      </Layout>
   );
}
