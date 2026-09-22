import { faArrowUpRightFromSquare, faCheck } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { useSuspenseQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useLoaderData } from "react-router";
import { BreadcrumbItem, Breadcrumbs } from "@/components/Breadcrumbs.tsx";
import Button from "@/elements/Button.tsx";
import PageSection from "@/elements/PageSection.tsx";
import { InfoBox } from "../components/InfoBox.tsx";
import { LayoutMain } from "../components/LayoutMain.tsx";
import { formatIssueReportDeadlineHeading, getRemainingReportTime } from "../utils/date.ts";
import { useFormatters } from "../utils/format.ts";
import { appRoutes } from "../utils/routes.ts";
import type { ReportIssueLoaderData } from "./ReportIssuePage.loader.ts";

const DEADLINE_TICK_MS = 60_000;

export function ReportIssuePage() {
   const { electionConfigQuery } = useLoaderData<ReportIssueLoaderData>();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const electionConfigSlug = electionConfig.slug;
   const deadline = electionConfig.issue_report_deadline;
   const [now, setNow] = useState(() => new Date());
   const { t } = useLingui();
   const { formatDate } = useFormatters();

   useEffect(() => {
      const tick = () => setNow(new Date());
      const intervalId = window.setInterval(tick, DEADLINE_TICK_MS);

      const deadlineTime = new Date(deadline).getTime();
      let timeoutId: number | undefined;
      if (!Number.isNaN(deadlineTime)) {
         const msUntilDeadline = deadlineTime - Date.now();
         if (msUntilDeadline > 0) {
            timeoutId = window.setTimeout(tick, msUntilDeadline);
         }
      }

      return () => {
         window.clearInterval(intervalId);
         if (timeoutId !== undefined) {
            window.clearTimeout(timeoutId);
         }
      };
   }, [deadline]);

   const reportingOpen = getRemainingReportTime(deadline, now) !== null;
   const heading = formatIssueReportDeadlineHeading(deadline, now);

   const opensAt = formatDate(electionConfig.issue_report_opens_at);
   const closesAt = formatDate(electionConfig.issue_report_deadline);

   return (
      <LayoutMain title={t`Een fout melden`}>
         <PageSection className="max-w-5xl">
            <div>
               <Breadcrumbs>
                  <BreadcrumbItem
                     key="election-config"
                     to={appRoutes.electionConfigMunicipalityList(electionConfigSlug)}
                  >
                     {electionConfig.label}
                  </BreadcrumbItem>
                  <BreadcrumbItem key="report-issue" to={appRoutes.reportIssue(electionConfigSlug)}>
                     <Trans>Fout melden</Trans>
                  </BreadcrumbItem>
               </Breadcrumbs>
               <h1>
                  <Trans>Een fout melden</Trans>
               </h1>
            </div>

            <p>
               <Trans>
                  Denkt u dat er een fout is gemaakt bij het tellen, opschrijven of het overtypen van de stemmen? Dan
                  kunt u daar een melding van maken bij het centraal stembureau.
               </Trans>
            </p>

            <InfoBox>
               <h4 className="font-bold">{heading}</h4>
               <p>
                  <Trans>
                     Een melding aan het centraal stembureau kan van {opensAt} tot {closesAt} (uiterlijk 48 uur voor de
                     zitting van het centraal stembureau). Meldingen die later binnenkomen worden niet in behandeling
                     genomen.
                  </Trans>
               </p>
            </InfoBox>

            <section className="flex flex-col gap-3">
               <h2>
                  <Trans>Waarvoor kunt u een melding maken?</Trans>
               </h2>
               <p>
                  <Trans>
                     U kunt een melding maken van mogelijke fouten die zijn gemaakt bij het tellen, opschrijven of
                     overtypen van de stemmen in de uitslagensoftware. Dit kan voor de processen-verbaal van het lokaal
                     stembureau, het gemeentelijk stembureau, het hoofdstembureau, het briefstembureau en het nationaal
                     briefstembureau.
                  </Trans>
               </p>
               <h2>
                  <Trans>Wat wordt er met een melding gedaan?</Trans>
               </h2>
               <p>
                  <Trans>
                     Nadat we je melding hebben ontvangen, zoeken we uit wat er aan de hand is. Als dat nodig is, nemen
                     we contact op met de gemeente of het stembureau. In sommige gevallen kan er een hertelling
                     plaatsvinden. Als blijkt dat er inderdaad een fout is gemaakt, bijvoorbeeld bij het tellen van de
                     stemmen, dan wordt die fout hersteld. De correctie wordt vastgelegd in een corrigendum en openbaar
                     gemaakt door dit te publiceren. Je ontvangt geen persoonlijk bericht over wat er met je melding is
                     gedaan.
                  </Trans>
               </p>
               <h2>
                  <Trans>Punten waar uw melding aan moet voldoen</Trans>
               </h2>
               <ul className="m-0 flex list-none flex-col gap-4 p-0">
                  <ChecklistItem>
                     <Trans>De melding moet voor {closesAt} bij de Kiesraad binnen zijn.</Trans>
                  </ChecklistItem>
                  <ChecklistItem>
                     <Trans>
                        De melding moet gaan over een mogelijke fout in het (op)tellen van de stemmen in het
                        proces-verbaal of in het digitale bestand van de gemeente. Andere klachten, zoals over een
                        stembureau dat te laat open was, horen thuis bij de zitting van het betreffende stembureau.
                     </Trans>
                  </ChecklistItem>
                  <ChecklistItem>
                     <Trans>
                        De melding moet duidelijk en onderbouwd zijn: geef aan wat er precies fout is gegaan, in welke
                        gemeente of bij welk stembureau, en waar de fout in zit.
                     </Trans>
                  </ChecklistItem>
                  <ChecklistItem>
                     <Trans>
                        De melding moet gaan over iets wat u zelf heeft gezien of meegemaakt, niet over iets wat u van
                        iemand anders heeft gehoord.
                     </Trans>
                  </ChecklistItem>
                  <ChecklistItem>
                     <Trans>Vermeld geen persoonsgegevens in uw melding; dat is niet nodig.</Trans>
                  </ChecklistItem>
               </ul>

               {electionConfig.report_error_url && (
                  <Button
                     disabled={!reportingOpen}
                     href={electionConfig.report_error_url}
                     target="_blank"
                     rel="noopener noreferrer"
                  >
                     <Trans>Meld een fout</Trans>
                     <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                  </Button>
               )}
            </section>
         </PageSection>
      </LayoutMain>
   );
}

function ChecklistItem({ children }: { children: ReactNode }) {
   return (
      <li className="flex items-start gap-2">
         <FontAwesomeIcon icon={faCheck} className="mt-1 size-4 shrink-0 text-(--c-done)" />
         <span>{children}</span>
      </li>
   );
}
