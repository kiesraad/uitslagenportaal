import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useElectionConfig, useRegion, useRegions } from "../../hooks/queries.ts";
import { formatDate } from "../../utils/date.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function CSBMunicipalityListPage() {
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { regionSlug } = useParams<{ regionSlug: string }>();

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
   const {
      data: regions,
      isLoading: isRegionsLoading,
      isError: isRegionsError,
      error: regionsError,
      refetch: refetchRegions,
   } = useRegions(electionConfigSlug, undefined, "GEMEENTE", regionSlug);

   const regionLabels = getRegionLabels(electionConfig?.csb_type);

   const isLoading = isElectionLoading || isRegionLoading || isRegionsLoading;
   const isError = isElectionError || isRegionError || isRegionsError || !electionConfig || !region || !regions;

   const csbResultsRoute = appRoutes.csbResults(electionConfigSlug ?? "", regionSlug ?? "");
   const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfigSlug ?? "", regionSlug ?? "");

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElection();
               void refetchRegion();
               void refetchRegions();
            }}
            entityLabel={regionLabels.singular}
            errors={[electionError, regionError, regionsError]}
         />
      );
   }

   return (
      <Layout
         title={`Telresultaten ${electionConfig.label}`}
         description={`Bekijk de telresultaten per gemeente van de ${electionConfig.label}.`}
      >
         <PageTop
            title={`${regionLabels.singular} - ${region.region_name}`}
            subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
            breadcrumb={[
               { href: appRoutes.home(), label: "Home" },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ""),
                  label: electionConfig.label,
               },
               { href: appRoutes.csbResults(electionConfigSlug ?? "", regionSlug ?? ""), label: region.region_name },
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
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="GEMEENTE" />
      </Layout>
   );
}
