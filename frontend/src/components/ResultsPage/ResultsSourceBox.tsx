import { faHourglass } from "@fortawesome/free-regular-svg-icons";
import { faArrowRight, faMaximize } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { useSuspenseQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { electionConfigQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import { appRoutes } from "@/utils/routes.ts";
import { InfoBox } from "../InfoBox";

type Props = {
   previewUrl?: string | null;
};

export default function ResultsSourceBox({ previewUrl }: Props) {
   const { t } = useLingui();
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(electionConfigSlug));
   const { formatTimelineDate } = useFormatters();
   const deadline = formatTimelineDate(electionConfig.issue_report_deadline);

   return (
      <div className="counting-results-infobox">
         <InfoBox>
            <h4>
               <Trans>Waar komen deze telresultaten vandaan?</Trans>
            </h4>
            <span className="mb-2">
               <Trans>
                  De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het
                  proces-verbaal dat gemaakt is na het tellen van de stemmen.
               </Trans>
            </span>
            {previewUrl ? (
               <>
                  <div className="results-image-container mb-2">
                     <div className="results-image-resize" aria-hidden="true">
                        <FontAwesomeIcon icon={faMaximize} />
                     </div>
                     <img src={previewUrl} alt={t`Proces-verbaal`} className="results-image" />
                  </div>
                  <p className="mb-3">
                     <a href={previewUrl}>
                        <Trans>Bekijk het proces-verbaal</Trans>
                        <FontAwesomeIcon icon={faArrowRight} />
                     </a>
                  </p>
               </>
            ) : (
               <div className="results-image-container results-image-pending mb-2">
                  <FontAwesomeIcon icon={faHourglass} className="results-image-pending-icon" aria-hidden="true" />
                  <p className="results-image-pending-title">
                     <Trans>Het proces-verbaal is nog niet ontvangen</Trans>
                  </p>
                  <p className="results-image-pending-text">
                     <Trans>Het verschijnt hier zodra het is binnengekomen.</Trans>
                  </p>
               </div>
            )}
            <span className="mb-1">
               <Trans>
                  Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de stemmen. Fouten die na{" "}
                  {deadline} worden gemeld, kunnen we nog onderzoeken en herstellen. Dan kan de juiste informatie mee in
                  de officiele uitslag.
               </Trans>
            </span>
            <p>
               <Link to={appRoutes.reportIssue(electionConfigSlug ?? "")}>
                  <Trans>Meld een fout of iets dat niet klopt</Trans>
                  <FontAwesomeIcon icon={faArrowRight} />
               </Link>
            </p>
         </InfoBox>
      </div>
   );
}
