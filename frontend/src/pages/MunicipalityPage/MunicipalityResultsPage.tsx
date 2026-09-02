import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import HtmlHead from "@/components/HtmlHead.tsx";
import { electionConfigQuery, regionQuery } from "@/hooks/queries.ts";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import MunicipalityPageLayout from "./MunicipalityPageLayout.tsx";

export function municipalityResultsLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
      };
   };
}

export type MunicipalityLoaderData = Awaited<ReturnType<ReturnType<typeof municipalityResultsLoader>>>;

export function MunicipalityResultsPage() {
   const { t } = useLingui();
   const { electionConfigQuery, regionQuery } = useLoaderData<MunicipalityLoaderData>();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);

   // Named rather than inlined, so the catalogue carries `{regionName}` instead of `{0}`.
   const regionName = region.region_name;
   const municipalityTitle = t`Gemeente ${regionName}`;

   return (
      <MunicipalityPageLayout electionConfig={electionConfig} region={region} municipalityTitle={municipalityTitle}>
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
      </MunicipalityPageLayout>
   );
}
