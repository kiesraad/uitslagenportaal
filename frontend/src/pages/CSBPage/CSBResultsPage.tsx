import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useElectionConfig, useRegion } from "../../hooks/queries.ts";
import { formatDate } from "../../utils/date.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function CSBResultsPage() {
   const { electionConfigSlug, regionSlug: regionSlugParam } = useParams<{
      electionConfigSlug: string;
      regionSlug: string;
   }>();
   const regionSlug = decodeURIComponent(regionSlugParam ?? "");
   const csbResultsRoute = appRoutes.csbResults(electionConfigSlug ?? "", regionSlug);
   const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfigSlug ?? "", regionSlug);

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
   } = useRegion(electionConfigSlug, regionSlug);

   const regionLabels = getRegionLabels(electionConfig?.csb_type);

   const isLoading = isElectionLoading || isRegionLoading;
   const isError = isElectionError || isRegionError || !electionConfig || !region;

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElection();
               void refetchRegion();
            }}
            entityLabel={regionLabels.singular}
            errors={[electionError, regionError]}
         />
      );
   }

   return (
      <Layout title="Resultaten">
         <PageTop
            title={`${regionLabels.singular} - ${region.region_name}`}
            subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
            breadcrumb={[
               { href: appRoutes.home(), label: "Home" },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ""),
                  label: electionConfig.label,
               },
               { href: appRoutes.csbResults(electionConfigSlug ?? "", regionSlug), label: region.region_name },
            ]}
            tabs={
               <SharedTabs
                  tabs={[
                     {
                        label: `${regionLabels.whole} ${regionLabels.singular.toLowerCase()}`,
                        value: csbResultsRoute,
                        activePatterns: [csbResultsRoute],
                     },
                     {
                        label: "Per gemeente",
                        value: csbMunicipalityListRoute,
                        activePatterns: [csbMunicipalityListRoute],
                     },
                  ]}
               />
            }
         />
         <div className="page-main page-main-two-columns">
            <div className="page-space-3">
               <RegionResultsContent
                  intro={
                     <>
                        Het hoofdstembureau heeft de telresultaten van alle gemeentes in {region.region_name}{" "}
                        gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze
                        zijn opgenomen in het proces-verbaal van het hoofdstembureau.
                     </>
                  }
                  voteCounts={region.vote_counts}
                  turnoutVotes={region.voter_turnout_counts}
                  reports={{
                     description: `Onderstaande documenten bevatten de laatste telresultaten van ${regionLabels.article} ${regionLabels.singular.toLowerCase()}, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand.`,
                     documents: region.documents,
                  }}
                  timelineVariant={region.timeline_variant}
                  timelineEntries={electionConfig.timeline_entries ?? []}
                  issueReportDeadline={electionConfig.issue_report_deadline}
                  notPublishedRegionLabel={region.region_name}
               />
            </div>
         </div>
      </Layout>
   );
}
