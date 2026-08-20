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
import { getPartyVoteCount } from "../../utils/voteCounts.ts";

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
      refetch: refetchElection,
   } = useElectionConfig(electionConfigSlug);
   const {
      data: region,
      isLoading: isRegionLoading,
      isError: isRegionError,
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
            entityLabel={t`Gemeente`}
            entityLabelInline={t`gemeente`}
         />
      );
   }

   const partyName = getPartyVoteCount(region.vote_counts, partySlug)?.party.registered_name ?? t`Lijst`;
   const regionName = region.region_name;
   const publishedAt = formatDate(region.results_available_at);
   const pageTitle = `${t`Telresultaten gemeente`}\n${regionName}`;
   const documentTitle = t`Telresultaten gemeente – ${regionName}`;

   return (
      <Layout title={documentTitle} description={documentTitle}>
         <PageTop
            title={pageTitle}
            subtitle={t`Geplaatst op: ${publishedAt}`}
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
