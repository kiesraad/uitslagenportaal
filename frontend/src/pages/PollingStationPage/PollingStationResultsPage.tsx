import { useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary";
import PageTop from "../../components/PageTop";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent";
import { useElectionConfig, useRegion } from "../../hooks/queries";
import { useFormatters } from "../../utils/format";
import { getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";

export default function PollingStationResultsPage() {
   const {
      electionConfigSlug: electionConfigSlugParam,
      regionSlug: parentRegionSlugParam,
      pollingStationSlug: pollingStationSlugParam,
      csbSlug: csbSlugParam,
   } = useParams<{
      electionConfigSlug: string;
      regionSlug: string;
      pollingStationSlug: string;
      csbSlug?: string;
   }>();

   const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? "");
   const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? "");
   const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? "");
   const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined;
   const { t } = useLingui();
   const { formatDate } = useFormatters();

   const {
      data: electionConfig,
      isLoading: isElectionLoading,
      isError: isElectionError,
      error: electionError,
      refetch: refetchElection,
   } = useElectionConfig(electionConfigSlug);
   const {
      data: region,
      isLoading: isRegionLoading,
      isError: isRegionError,
      error: regionError,
      refetch: refetchRegion,
   } = useRegion(electionConfigSlug, parentRegionSlug, csbSlug);
   const {
      data: pollingStation,
      isLoading: isPollingStationLoading,
      isError: isPollingStationError,
      error: pollingStationError,
      refetch: refetchPollingStation,
   } = useRegion(electionConfigSlug, pollingStationSlug, csbSlug, parentRegionSlug);

   const isLoading = isElectionLoading || isRegionLoading || isPollingStationLoading;
   const isError =
      isElectionError || isRegionError || isPollingStationError || !electionConfig || !region || !pollingStation;

   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfigSlug,
      parentRegionSlug,
      csbSlug,
   );
   const pollingStationResultsRoute = appRoutes.pollingStationResults(
      electionConfigSlug,
      parentRegionSlug,
      pollingStationSlug,
      csbSlug,
   );

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElection();
               void refetchRegion();
               void refetchPollingStation();
            }}
            errors={[electionError, regionError, pollingStationError]}
            entityLabel={t`Stembureau`}
         />
      );
   }

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
               { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
               getCsbCrumb(region, electionConfigSlug),
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
