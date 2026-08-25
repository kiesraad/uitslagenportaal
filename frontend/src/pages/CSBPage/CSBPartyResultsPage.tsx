import { Trans, useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import IssueNotice from "../../components/ResultsPage/IssueNotice.tsx";
import PartyVoteMatrixTable from "../../components/ResultsPage/PartyVoteMatrixTable.tsx";
import ResultsNotPublished from "../../components/ResultsPage/ResultsNotPublished.tsx";
import ResultsPageIndex from "../../components/ResultsPage/ResultsPageIndex";
import ResultsTimeline from "../../components/ResultsPage/ResultsTimeline.tsx";
import { useElectionConfig, usePartyVoteMatrix, useRegion } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { getPartyVoteCount } from "../../utils/voteCounts.ts";

export function CSBPartyResultsPage() {
   const {
      electionConfigSlug,
      regionSlug: regionSlugParam,
      partySlug: partySlugParam,
   } = useParams<{ electionConfigSlug: string; regionSlug: string; partySlug: string }>();
   const regionSlug = decodeURIComponent(regionSlugParam ?? "");
   const partySlug = decodeURIComponent(partySlugParam ?? "");
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
   } = useRegion(electionConfigSlug, regionSlug);
   const {
      data: partyVoteMatrix,
      isLoading: isPartyVoteMatrixLoading,
      isError: isPartyVoteMatrixError,
      refetch: refetchPartyVoteMatrix,
   } = usePartyVoteMatrix(region?.election_slug, regionSlug, partySlug);

   const regionLabels = getRegionLabels(electionConfig?.csb_type);
   const partyName = partyVoteMatrix?.party.registered_name ?? partySlug;
   const partyListNumber = getPartyVoteCount(region?.vote_counts, partySlug)?.party.list_number;

   const isLoading = isElectionLoading || isRegionLoading || isPartyVoteMatrixLoading;
   const isError =
      isElectionError || isRegionError || isPartyVoteMatrixError || !electionConfig || !region || !partyVoteMatrix;

   const hasResults = (partyVoteMatrix?.rows.length ?? 0) > 0;

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElection();
               void refetchRegion();
               void refetchPartyVoteMatrix();
            }}
            entityLabel={t(regionLabels.singular)}
         />
      );
   }

   const listNumber = partyListNumber ?? "-";
   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   const publishedAt = formatDate(region.results_available_at);

   const resultsPageContent = (
      <>
         <ResultsPageIndex />
         <section id="telresultaten" className="party-vote-matrix-section">
            <h2 className="text-lg mb-4.5 font-medium">
               <Trans>Telresultaten lijst {listNumber}</Trans>
            </h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>

            <p className="mb-4 max-w-160">
               <Trans>
                  Het centraal stembureau heeft de telresultaten van alle gemeenten en kieskringen gecontroleerd,
                  overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het
                  proces-verbaal van het centraal stembureau.
               </Trans>
            </p>
            <PartyVoteMatrixTable matrix={partyVoteMatrix} />
         </section>
      </>
   );

   return (
      <Layout title={t`Resultaten`}>
         <PageTop
            title={`${t`Telresultaten ${regionType} ${regionName}`}\n ${partyName}`}
            subtitle={t`Geplaatst op: ${publishedAt}`}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ""),
                  label: electionConfig.label,
               },
               { href: appRoutes.csbResults(electionConfigSlug ?? "", regionSlug), label: region.region_name },
               { href: appRoutes.csbPartyResults(electionConfigSlug ?? "", regionSlug, partySlug), label: partyName },
            ]}
         />
         <div className="page-main">
            <div className="page-space-3 party-vote-matrix-page">
               {!hasResults ? <ResultsNotPublished regionLabel={region.region_name} /> : resultsPageContent}
               <ResultsTimeline variant={region.timeline_variant} entries={electionConfig.timeline_entries ?? []} />
               <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
            </div>
         </div>
      </Layout>
   );
}
