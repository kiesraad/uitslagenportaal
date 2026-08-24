import { Outlet, useParams } from "react-router";
import { Layout } from "@/components/Layout.tsx";
import { PageQueryBoundary } from "@/components/PageQueryBoundary.tsx";
import PageTop from "@/components/PageTop.tsx";
import SharedTabs from "@/components/SharedTabs.tsx";
import { useElectionConfig, useRegion } from "@/hooks/queries.ts";
import { formatDate } from "@/utils/date.ts";
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
            entityLabel="Gemeente"
            errors={[electionConfigError, regionError]}
         />
      );
   }

   const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0;
   const municipalityTitle = `Gemeente ${region.region_name}`;

   return (
      <Layout>
         <PageTop
            title={municipalityTitle}
            subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
            breadcrumb={[
               { href: appRoutes.home(), label: "Home" },
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
                           label: "Resultaten per stembureau",
                           value: municipalityPollingstationListRoute,
                           activePatterns: [municipalityPollingstationListRoute],
                        },
                        {
                           label: "Hele gemeente",
                           value: municipalityResultsRoute,
                           activePatterns: [municipalityResultsRoute],
                        },
                     ]}
                  />
               )
            }
         />
         <Outlet context={{ electionConfig, municipalityTitle, region, electionConfigSlug, regionSlug, csbSlug }} />
      </Layout>
   );
}
