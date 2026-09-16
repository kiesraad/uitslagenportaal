import { faArrowRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Trans } from "@lingui/react/macro";
import { Link, useParams } from "react-router";
import { useFormatters } from "@/utils/format.ts";
import { appRoutes } from "@/utils/routes.ts";
import { InfoBox } from "../InfoBox";

type IssueNoticeProps = {
   issueReportDeadline: string;
};

export default function IssueNotice({ issueReportDeadline }: IssueNoticeProps) {
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { formatTimelineDate } = useFormatters();
   const deadline = formatTimelineDate(issueReportDeadline);

   return (
      <section id="fout-melden">
         <InfoBox>
            <h4>
               <Trans>Klopt er iets niet?</Trans>
            </h4>
            <span>
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
      </section>
   );
}
