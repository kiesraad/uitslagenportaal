import { useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout";
import { PageQueryBoundary } from "../../components/PageQueryBoundary";
import PageTop from "../../components/PageTop";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent";
import { useElectionConfig, useRegion } from "../../hooks/queries";
import { useFormatters } from "../../utils/format";
import { getCsbCrumb } from "../../utils/region";
import { appRoutes } from "../../utils/routes";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts";
import { NotFoundPage } from "../NotFoundPage";

export default function PollingStationPartyResultsPage() {
   const {
      electionConfigSlug: electionConfigSlugParam,
      parentRegionSlug: parentRegionSlugParam,
      pollingStationSlug: pollingStationSlugParam,
      partySlug: partySlugParam,
      csbSlug: csbSlugParam,
   } = useParams<{
      electionConfigSlug: string;
      parentRegionSlug: string;
      pollingStationSlug: string;
      partySlug: string;
      csbSlug?: string;
   }>();

   const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? "");
   const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? "");
   const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? "");
   const partySlug = decodeURIComponent(partySlugParam ?? "");
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
   const pollingStationPartyResultsRoute = appRoutes.pollingStationPartyResults(
      electionConfigSlug,
      parentRegionSlug,
      pollingStationSlug,
      partySlug,
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

   const partyName = getPartyVoteCount(pollingStation.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const stationName = pollingStation.region_name;
   const publishedAt = formatDate(region.results_available_at);
   const pageTitle = `${t`Telresultaten stembureau`}\n${stationName}`;
   const documentTitle = t`Telresultaten stembureau – ${stationName}`;

   // Only an unknown party slug is a 404; empty results mean "not published yet"
   const hasAnyResults = (pollingStation.vote_counts?.length ?? 0) > 0;
   if (hasAnyResults && !hasParty(pollingStation.vote_counts, partySlug)) {
      return <NotFoundPage />;
   }

   return (
      <Layout title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={t`Geplaatst op: ${publishedAt}`}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
               getCsbCrumb(region, electionConfigSlug),
               { href: municipalityPollingstationListRoute, label: region.region_name },
               { href: pollingStationResultsRoute, label: pollingStation.region_name },
               { href: pollingStationPartyResultsRoute, label: partyName },
            ]}
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <PartyCandidatesResultsContent
                  voteCounts={pollingStation.vote_counts}
                  partySlug={partySlug}
                  issueReportDeadline={electionConfig.issue_report_deadline}
               />
            </div>
         </div>
      </Layout>
   );
}
