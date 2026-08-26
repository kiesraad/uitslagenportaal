import { Trans, useLingui } from "@lingui/react/macro";
import { useOutletContext } from "react-router";
import type { ElectionConfig, Region } from "@/api/types.ts";
import HtmlHead from "@/components/HtmlHead.tsx";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";

export function MunicipalityResultsPage() {
   const { electionConfig, region, municipalityTitle } = useOutletContext<{
      electionConfig: ElectionConfig;
      region: Region;
      municipalityTitle: string;
   }>();
   const { t } = useLingui();
   const regionName = region.region_name;

   return (
      <>
         <HtmlHead title={t`Resultaten ${municipalityTitle}`} />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <RegionResultsContent
                  intro={
                     <Trans>
                        Het gemeentelijk stembureau heeft de telresultaten van alle stembureaus in {regionName}{" "}
                        gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze
                        zijn opgenomen in het proces-verbaal van de gemeente.
                     </Trans>
                  }
                  voteCounts={region.vote_counts}
                  turnoutVotes={region.voter_turnout_counts}
                  reports={{
                     description: t`Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.`,
                     documents: region.documents,
                  }}
                  timelineVariant={region.timeline_variant}
                  timelineEntries={electionConfig.timeline_entries ?? []}
                  issueReportDeadline={electionConfig.issue_report_deadline}
                  notPublishedRegionLabel={region.region_name}
               />
            </div>
         </div>
      </>
   );
}
