import { Trans } from "@lingui/react/macro";
import PageIndex from "../PageIndex";

type ResultsPageIndexVariant = "full" | "party";

type Props = {
   variant?: ResultsPageIndexVariant;
};

export default function ResultsPageIndex({ variant = "full" }: Props) {
   // Built inside the component so the labels are re-created when the language
   // changes, rather than captured once at module load.
   const telresultatenLink = {
      label: (
         <Trans>
            <span className="font-semibold">Telresultaten</span> zoals ze meetellen in de officiele uitslag
         </Trans>
      ),
      url: "#telresultaten",
   };

   const timelineLink = {
      label: (
         <Trans>
            <span className="font-semibold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen
         </Trans>
      ),
      url: "#results-timeline",
   };

   const issueReportLink = {
      label: (
         <span className="font-semibold">
            <Trans>Hoe u een fout kunt melden</Trans>
         </span>
      ),
      url: "#fout-melden",
   };

   const links =
      variant === "party" ? [telresultatenLink, issueReportLink] : [telresultatenLink, timelineLink, issueReportLink];

   return <PageIndex links={links} />;
}
