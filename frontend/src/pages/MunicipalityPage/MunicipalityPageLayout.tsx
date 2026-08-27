import { useLingui } from "@lingui/react/macro";
import { Outlet, useParams } from "react-router";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { PageQueryBoundary } from "@/components/PageQueryBoundary.tsx";
import PageTop from "@/components/PageTop.tsx";
import SharedTabs from "@/components/SharedTabs.tsx";
import { useElectionConfig, useRegion } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import { getCsbCrumb } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

export default function MunicipalityPageLayout() {
   const {
      electionConfigSlug,
      regionSlug: regionSlugParam,
      csbSlug: csbSlugParam,
   } = useParams<{ electionConfigSlug: string; regionSlug: string; csbSlug?: string }>();
   const regionSlug = decodeURIComponent(regionSlugParam ?? "");
   const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined;
   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfigSlug ?? "",
      regionSlug,
      csbSlug,
   );
   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug ?? "", regionSlug, csbSlug);
   const { t } = useLingui();
   const { formatDate } = useFormatters();

   const {
      data: electionConfig,
      isLoading: isElectionConfigLoading,
      isError: isElectionConfigError,
      error: electionConfigError,
      refetch: refetchElectionConfig,
   } = useElectionConfig(electionConfigSlug);
   const {
      data: region,
      isLoading: isRegionLoading,
      isError: isRegionError,
      error: regionError,
      refetch: refetchRegion,
   } = useRegion(electionConfigSlug, regionSlug, csbSlug);

   const isLoading = isElectionConfigLoading || isRegionLoading;
   const isError = isElectionConfigError || isRegionError || !electionConfig || !region;

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElectionConfig();
               void refetchRegion();
            }}
            errors={[electionConfigError, regionError]}
            entityLabel={t`Gemeente`}
         />
      );
   }

   const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0;
   const regionName = region.region_name;
   const municipalityTitle = t`Gemeente ${regionName}`;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;

   return (
      <LayoutMain>
         <PageTop
            title={municipalityTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ""),
                  label: electionConfig.label,
               },
               getCsbCrumb(region, electionConfigSlug ?? ""),
               { href: municipalityPollingstationListRoute, label: municipalityTitle },
            ]}
            tabs={
               hasResults && (
                  <SharedTabs
                     tabs={[
                        {
                           label: t`Resultaten per stembureau`,
                           value: municipalityPollingstationListRoute,
                           activePatterns: [municipalityPollingstationListRoute],
                        },
                        {
                           label: t`Hele gemeente`,
                           value: municipalityResultsRoute,
                           activePatterns: [municipalityResultsRoute],
                        },
                     ]}
                  />
               )
            }
         />
         <Outlet context={{ electionConfig, municipalityTitle, region, electionConfigSlug, regionSlug, csbSlug }} />
      </LayoutMain>
   );
}
