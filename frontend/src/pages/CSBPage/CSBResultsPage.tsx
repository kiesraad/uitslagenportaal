import { Trans, useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import RegionResultsContent from "../../components/ResultsPage/RegionResultsContent.tsx";
import ResultsPageColumns from "../../components/ResultsPage/ResultsPageColumns.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import { CSBResultsComponent } from "@/components/ResultsPage/CSBResultsComponent.tsx";


export function csbResultsLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params, "csb");

      await Promise.all([queryClient.query(electionConfigQueryOptions), queryClient.query(regionQueryOptions)]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof csbResultsLoader>>>;

export function CSBResultsPage() {
   const { electionConfigQuery, regionQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);

   const regionLabels = getRegionLabels(electionConfig.csb_type);
   const csbResultsRoute = appRoutes.csbResults(electionConfig.slug, region.slug);
   const csbMunicipalityListRoute = appRoutes.csbMunicipalityList(electionConfig.slug, region.slug);

   const regionType = t(regionLabels.singular);
   const regionName = region.region_name;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;

   return (
      <LayoutMain title={t`Telresultaten ${regionType} ${regionName}`}>
         <PageTop
            title={t`${regionType} - ${regionName}`}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               { label: region.region_name },
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
         <CSBResultsComponent electionConfig={electionConfig} region={region} />
      </LayoutMain>
   );
}
