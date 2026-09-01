import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function csbMunicipalityListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);
      // The region parameter names the CSB the gemeentes report to, not their parent region.
      const regionsQueryOptions = regionsQuery(
         { electionConfigSlug: params.electionConfigSlug, csbSlug: params.regionSlug },
         "GEMEENTE",
      );

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
         queryClient.ensureQueryData(regionsQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         regionsQuery: regionsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof csbMunicipalityListLoader>>>;

export function CSBMunicipalityListPage() {
   const { electionConfigQuery, regionQuery, regionsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved every query, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: regions } = useSuspenseQuery(regionsQuery);

   const regionLabels = getRegionLabels(electionConfig.csb_type);
   const csbResultsRoute = appRoutes.csbResults(electionConfig.slug, region.slug);
   const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfig.slug, region.slug);

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;
   const electionLabel = electionConfig.label;

   return (
      <LayoutMain
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per gemeente van de ${electionLabel}.`}
      >
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               { href: csbResultsRoute, label: region.region_name },
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
      </LayoutMain>
   );
}
