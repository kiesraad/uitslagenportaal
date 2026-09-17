import { faArrowRight, faMaximize } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans, useLingui } from "@lingui/react/macro";
import { Link, useParams } from "react-router";
import { appRoutes } from "@/utils/routes.ts";
import { InfoBox } from "../InfoBox";

/** Placeholder scan until proces-verbaal documents are served from the API. */
const STUB_PV_HREF = "/images/results_image.png";

export default function ResultsSourceBox() {
   const { t } = useLingui();
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const deadline = "14 december 10:00";

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
            <div className="results-image-container mb-2">
               <div className="results-image-resize" aria-hidden="true">
                  <FontAwesomeIcon icon={faMaximize} />
               </div>
               <img src={STUB_PV_HREF} alt={t`Voorbeeld van een proces-verbaal`} className="results-image" />
            </div>
            <p className="mb-3">
               <a href={STUB_PV_HREF}>
                  <Trans>Bekijk het proces-verbaal</Trans>
                  <FontAwesomeIcon icon={faArrowRight} />
               </a>
            </p>
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
