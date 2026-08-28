import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent";
import { electionConfigQuery, regionQuery } from "../../hooks/queries";
import { useFormatters } from "../../utils/format";
import { getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";

/** The stembureau and the gemeente it belongs to, for both stembureau pages. */
export function pollingStationLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);
      // The stembureau is the region being fetched here; the gemeente in the URL is its parent.
      const pollingStationQueryOptions = regionQuery({
         electionConfigSlug: params.electionConfigSlug,
         regionSlug: params.pollingStationSlug,
         csbSlug: params.csbSlug,
         parentRegionSlug: params.regionSlug,
      });

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
         queryClient.ensureQueryData(pollingStationQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         pollingStationQuery: pollingStationQueryOptions,
      };
   };
}

export type PollingStationLoaderData = Awaited<ReturnType<ReturnType<typeof pollingStationLoader>>>;

export default function PollingStationResultsPage() {
   const { electionConfigQuery, regionQuery, pollingStationQuery } = useLoaderData<PollingStationLoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved every query, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: pollingStation } = useSuspenseQuery(pollingStationQuery);

   const csbSlug = region.csb_slug ?? undefined;
   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfig.slug,
      region.slug,
      csbSlug,
   );
   const pollingStationResultsRoute = appRoutes.pollingStationResults(
      electionConfig.slug,
      region.slug,
      pollingStation.slug,
      csbSlug,
   );

   const stationName = pollingStation.region_name;
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten stembureau`}\n${stationName}`;
   const documentTitle = t`Telresultaten stembureau – ${stationName}`;

   return (
      <LayoutMain title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfig.slug), label: electionConfig.label },
               getCsbCrumb(region, electionConfig.slug),
               { href: municipalityPollingstationListRoute, label: t`Gemeente ${regionName}` },
               { href: pollingStationResultsRoute, label: pollingStation.region_name },
            ]}
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <RegionResultsContent
                  intro={t`De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.`}
                  voteCounts={pollingStation.vote_counts}
                  turnoutVotes={pollingStation.voter_turnout_counts}
                  timelineVariant={pollingStation.timeline_variant}
                  timelineEntries={pollingStation.timeline_entries ?? []}
                  issueReportDeadline={electionConfig.issue_report_deadline}
                  notPublishedRegionLabel={region.region_name}
               />
            </div>
         </div>
      </LayoutMain>
   );
}
