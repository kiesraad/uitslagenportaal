import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { HSBTimeline } from "@/components/Timeline/HSBTimeline.tsx";
import { queryClient } from "@/queryClient.ts";
import { ApiError } from "../../api/client.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getCsbCrumb, getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import type { Route } from "./+types/HSBResultsPage";

export async function loadHSBResults(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   const [electionConfig] = await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "hsb")),
   ]);

   if (!electionConfig.has_hsb) {
      throw new ApiError("Election has no HSBs", 404);
   }
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadHSBResults(queryClient, args);

export default function HSBResultsPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "hsb"));

   const regionLabels = getRegionLabels("KIESKRING");
   const hsbResultsRoute = appRoutes.hsbResults(electionConfig.slug, region.slug);
   const hsbMunicipalityListRoute = appRoutes.hsbMunicipalityList(electionConfig.slug, region.slug);

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const regionWithArticle = t(regionLabels.withArticle);

   return (
      <LayoutMain title={t`Telresultaten ${regionType} ${regionName}`}>
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               getCsbCrumb(region, electionConfig),
               { label: region.region_name },
            ]}
            tabs={
               <SharedTabs
                  tabs={[
                     {
                        label: t(regionLabels.whole),
                        value: hsbResultsRoute,
                        activePatterns: [hsbResultsRoute],
                     },
                     {
                        label: t`Per gemeente`,
                        value: hsbMunicipalityListRoute,
                        activePatterns: [hsbMunicipalityListRoute],
                     },
                  ]}
               />
            }
         />
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
               issueReportDeadline={electionConfig.issue_report_deadline}
               notPublishedRegionName={region.region_name}
               notPublishedRegionCategory={region.region_category}
               timeline={
                  <HSBTimeline
                     dates={electionConfig.timeline_dates ?? []}
                     documents={region.documents}
                     region={region}
                  />
               }
            />
         </ResultsPageColumns>
      </LayoutMain>
   );
}
