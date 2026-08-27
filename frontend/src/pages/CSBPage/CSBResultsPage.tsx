import { Trans, useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useElectionConfig, useRegion } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
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
            errors={[electionError, regionError]}
            entityLabel={t(regionLabels.singular)}
         />
      );
   }

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   // "de gemeente" / "het waterschap": article and noun as one translated
   // phrase, because which article a noun takes is language-specific.
   const regionWithArticle = t(regionLabels.withArticle);

   return (
      <LayoutMain title={t`Resultaten`}>
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
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
                        label: t(regionLabels.whole),
                        value: csbResultsRoute,
                        activePatterns: [csbResultsRoute],
                     },
                     {
                        label: t`Per gemeente`,
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
                  timelineVariant={region.timeline_variant}
                  timelineEntries={electionConfig.timeline_entries ?? []}
                  issueReportDeadline={electionConfig.issue_report_deadline}
                  notPublishedRegionLabel={region.region_name}
               />
            </div>
         </div>
      </LayoutMain>
   );
}
