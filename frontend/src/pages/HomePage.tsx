import { faHourglass } from "@fortawesome/free-regular-svg-icons";
import { faArrowUpRightFromSquare, faCircleNotch, faRotateRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { Link } from "react-router";
import Button from "@/elements/Button.tsx";
import PageSection from "@/elements/PageSection.tsx";
import type { ElectionConfig } from "../api/types.ts";
import { HeroGrid } from "../components/HomePage/HeroGrid.tsx";
import { LayoutMain } from "../components/LayoutMain.tsx";
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
      <LayoutMain title={t`Home`} description={t`De telresultaten van alle stembureaus in Nederland.`}>
         <PageSection className="relative grid flex-1 grid-cols-1 overflow-hidden bg-blue-100 lg:grid-cols-2 lg:gap-20">
            <div className="flex flex-col justify-center gap-3.5 sm:gap-6.5">
               <h1 className="max-w-xl font-bold font-title text-3xl sm:text-4xl">
                  <Trans>De telresultaten van alle stembureaus in Nederland.</Trans>
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
                        <FontAwesomeIcon icon={faCircleNotch} className="animate-spin" />
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
                     <Button onClick={() => refetch()}>
                        <FontAwesomeIcon icon={faRotateRight} />
                        <Trans>Opnieuw proberen</Trans>
                     </Button>
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

         {election_configs.length === 1 && (
            <>
               <PageSection className="flex max-w-5xl flex-col gap-4">
                  <h2>
                     <Trans>Hoe komt de uitslag tot stand?</Trans>
                  </h2>
                  <p>
                     <Trans>
                        Hieronder wordt stap voor stap uitgelegd hoe het resultaat van de verkiezing tot stand komt. Het
                        begint bij het stembureau en eindigt bij de definitieve uitslag die de Kiesraad publiceert. Bij
                        iedere stap is er controle, zodat de uitslag klopt.
                     </Trans>
                  </p>

                  <Timeline entries={timelineEntries} />
               </PageSection>

               <PageSection className="max-w-5xl pt-0!">
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
               </PageSection>
            </>
         )}
      </LayoutMain>
   );
}
