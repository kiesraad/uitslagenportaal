import { Trans, useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
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
      refetch: refetchElection,
   } = useElectionConfig(electionConfigSlug);
   const {
      data: region,
      isLoading: isRegionLoading,
      isError: isRegionError,
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
            entityLabel={t(regionLabels.singular)}
            entityLabelInline={t(regionLabels.inline)}
         />
      );
   }

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   const publishedAt = formatDate(region.results_available_at);
   // "de gemeente" / "het waterschap": article and noun as one translated
   // phrase, because which article a noun takes is language-specific.
   const regionWithArticle = t(regionLabels.withArticle);

   return (
      <Layout title={t`Resultaten`}>
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={t`Geplaatst op: ${publishedAt}`}
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
      </Layout>
   );
}
