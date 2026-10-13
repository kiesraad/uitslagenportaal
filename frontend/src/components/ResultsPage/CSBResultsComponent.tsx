import { Trans, useLingui } from "@lingui/react/macro";
import type { ElectionConfig, Region } from "../../api/types";
import RegionResultsContent from "./RegionResultsContent.tsx";
import ResultsPageColumns from "./ResultsPageColumns.tsx";

type Props = {
   electionConfig: ElectionConfig;
   region: Region;
   regionName: string;
   regionWithArticle: string;
};

export function CSBResultsComponent({ electionConfig, region, regionName, regionWithArticle }: Props) {
   const { t } = useLingui();

   return (
      <ResultsPageColumns
         previewUrl={region.certified_document_preview_url}
         documentUrl={region.certified_document_url}
      >
         <RegionResultsContent
            intro={
               <Trans>
                  Het hoofdstembureau heeft de telresultaten van alle gemeentes in {regionName} gecontroleerd,
                  overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in
                  het proces-verbaal van het hoofdstembureau.
               </Trans>
            }
            voteCounts={region.vote_counts}
            turnoutVotes={region.voter_turnout_counts}
            reports={{
               description: t`Onderstaande documenten bevatten de laatste telresultaten van ${regionWithArticle}, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.`,
               documents: region.documents,
            }}
            timelineVariant={region.timeline_variant}
            timelineEntries={electionConfig.timeline_entries ?? []}
            issueReportDeadline={electionConfig.issue_report_deadline}
            notPublishedRegionName={region.region_name}
            notPublishedRegionCategory={region.region_category}
         />
      </ResultsPageColumns>
   );
}
