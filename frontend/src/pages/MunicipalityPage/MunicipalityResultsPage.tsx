import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import HtmlHead from "@/components/HtmlHead.tsx";
import { GSBTimeline } from "@/components/Timeline/GSBTimeline.tsx";
import { electionConfigQuery, regionQuery } from "@/hooks/queries.ts";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns.tsx";
import MunicipalityPageLayout from "./MunicipalityPageLayout.tsx";

export async function loadMunicipalityResults(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "gsb")),
   ]);
}

export default function MunicipalityResultsPage() {
   const params = useParams();
   const { t } = useLingui();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "gsb"));

   // Named rather than inlined, so the catalogue carries `{regionName}` instead of `{0}`.
   const regionName = region.region_name;
   const municipalityTitle = t`Gemeente ${regionName}`;

   return (
      <MunicipalityPageLayout electionConfig={electionConfig} region={region} municipalityTitle={municipalityTitle}>
         <HtmlHead title={t`Resultaten ${municipalityTitle}`} />
         <ResultsPageColumns
            previewUrl={region.certified_document_preview_url}
            documentUrl={region.certified_document_url}
         >
            <RegionResultsContent
               intro={
                  <Trans>
                     Het gemeentelijk stembureau heeft de telresultaten van alle stembureaus in {regionName}{" "}
                     gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn
                     opgenomen in het proces-verbaal van de gemeente.
                  </Trans>
               }
               voteCounts={region.vote_counts}
               turnoutVotes={region.voter_turnout_counts}
               reports={{
                  description: t`Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.`,
                  documents: region.documents,
               }}
               issueReportDeadline={electionConfig.issue_report_deadline}
               notPublishedRegionName={region.region_name}
               notPublishedRegionCategory={region.region_category}
               timeline={
                  <GSBTimeline
                     variant={region.timeline_variant}
                     dates={electionConfig.timeline_dates ?? []}
                     documents={region.documents}
                     region={region}
                  />
               }
            />
         </ResultsPageColumns>
      </MunicipalityPageLayout>
   );
}
