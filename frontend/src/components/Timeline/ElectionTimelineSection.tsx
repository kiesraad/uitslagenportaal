import { Trans } from "@lingui/react/macro";
import { Link } from "react-router";
import type { ElectionConfig } from "@/api/types.ts";
import { GenericTimeline } from "@/components/Timeline/GenericTimeline.tsx";
import { ExternalLinkIcon } from "@/elements/ExternalLinkIcon.tsx";
import PageSection from "@/elements/PageSection.tsx";
import { appRoutes } from "@/utils/routes.ts";

type Props = {
   electionConfig: ElectionConfig;
};

export function ElectionTimelineSection({ electionConfig }: Props) {
   const electionLabel = electionConfig.label;

   return (
      <>
         <PageSection className="flex max-w-5xl flex-col gap-4">
            <h2>
               <Trans>Hoe komt de uitslag tot stand?</Trans>
            </h2>
            <p>
               <Trans>
                  Hieronder wordt stap voor stap uitgelegd hoe het resultaat van de verkiezing tot stand komt. Het
                  begint bij het stembureau en eindigt bij de definitieve uitslag die de Kiesraad publiceert. Bij iedere
                  stap is er controle, zodat de uitslag klopt.
               </Trans>
            </p>

            <GenericTimeline dates={electionConfig.timeline_dates} />
         </PageSection>

         <PageSection className="max-w-5xl pt-0!">
            <div className="home-info-box">
               <div className="home-info-body">
                  <h3>
                     <Trans>Benieuwd naar de resultaten in het stembureau waar u gestemd heeft?</Trans>
                  </h3>
                  <div className={"home-hero-card-link"}>
                     <span className="gemeente-chevron" aria-hidden="true">
                        ›
                     </span>
                     <Link to={appRoutes.electionConfigMunicipalityList(electionConfig.slug)}>
                        <Trans>Bekijk de tellingen per stembureau voor {electionLabel}</Trans>
                     </Link>
                  </div>
               </div>
            </div>

            <div className="home-external-links">
               <p>
                  <Trans>
                     Deze website is actief vanaf 1 dag vóór de verkiezingen tot drie maanden erna. Wilt u uitslagen van
                     eerdere verkiezingen bekijken?
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
                        <ExternalLinkIcon />
                     </a>
                  </span>
               </p>
            </div>
         </PageSection>
      </>
   );
}
