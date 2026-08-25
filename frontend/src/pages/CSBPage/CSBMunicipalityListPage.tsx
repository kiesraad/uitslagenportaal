import { useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useElectionConfig, useRegion, useRegions } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function CSBMunicipalityListPage() {
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { regionSlug } = useParams<{ regionSlug: string }>();
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
      data: regions,
      isLoading: isRegionsLoading,
      isError: isRegionsError,
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
            entityLabel={t(regionLabels.singular)}
         />
      );
   }

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   const publishedAt = formatDate(region.results_available_at);
   const electionLabel = electionConfig.label;

   return (
      <Layout
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per gemeente van de ${electionLabel}.`}
      >
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={t`Geplaatst op: ${publishedAt}`}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
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
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="GEMEENTE" />
      </Layout>
   );
}
