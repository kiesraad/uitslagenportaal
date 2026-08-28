import { useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import PartyCandidatesResultsContent from "../../components/ResultsPage/PartyCandidatesResultsContent.tsx";
import { useElectionConfig, useRegion } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getCsbCrumb } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount, hasParty } from "../../utils/voteCounts.ts";
import { NotFoundPage } from "../NotFoundPage.tsx";

export function MunicipalityPartyResultsPage() {
   const {
      electionConfigSlug: electionConfigSlugParam,
      regionSlug: parentRegionSlugParam,
      partySlug: partySlugParam,
      csbSlug: csbSlugParam,
   } = useParams<{ electionConfigSlug: string; regionSlug: string; partySlug: string; csbSlug?: string }>();

   const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? "");
   const regionSlug = decodeURIComponent(parentRegionSlugParam ?? "");
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
   } = useRegion(electionConfigSlug, regionSlug, csbSlug);

   const isLoading = isElectionLoading || isRegionLoading;
   const isError = isElectionError || isRegionError || !electionConfig || !region;

   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug, regionSlug, csbSlug);
   const municipalityPartyResultsRoute = appRoutes.municipalityPartyResults(
      electionConfigSlug,
      regionSlug,
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
            }}
            errors={[electionError, regionError]}
            entityLabel={t`Gemeente`}
         />
      );
   }

   // Only an unknown party slug is a 404; empty results mean "not published yet"
   const hasAnyResults = (region.vote_counts?.length ?? 0) > 0;
   if (hasAnyResults && !hasParty(region.vote_counts, partySlug)) {
      return <NotFoundPage />;
   }

   const partyName = getPartyVoteCount(region.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const pageTitle = `${t`Telresultaten gemeente`}\n${regionName}`;
   const documentTitle = t`Telresultaten gemeente – ${regionName}`;

   return (
      <Layout title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
               getCsbCrumb(region, electionConfigSlug),
               { href: municipalityResultsRoute, label: t`Gemeente ${regionName}` },
               { href: municipalityPartyResultsRoute, label: partyName },
            ]}
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <PartyCandidatesResultsContent
                  voteCounts={region.vote_counts}
                  partySlug={partySlug}
                  issueReportDeadline={electionConfig.issue_report_deadline}
               />
            </div>
         </div>
      </Layout>
   );
}
