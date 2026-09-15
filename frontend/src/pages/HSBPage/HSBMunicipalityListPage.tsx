import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { ApiError } from "../../api/client.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function hsbMunicipalityListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params, "hsb");
      const regionsQueryOptions = regionsQuery(params, "GEMEENTE");

      const [electionConfig] = await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
         queryClient.ensureQueryData(regionsQueryOptions),
      ]);

      if (!electionConfig.has_hsb) {
         throw new ApiError("Election has no HSBs", 404);
      }

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         regionsQuery: regionsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof hsbMunicipalityListLoader>>>;

export function HSBMunicipalityListPage() {
   const { electionConfigQuery, regionQuery, regionsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved every query, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: regions } = useSuspenseQuery(regionsQuery);

   const regionLabels = getRegionLabels("KIESKRING");
   const hsbResultsRoute = appRoutes.hsbResults(electionConfig.slug, region.slug);
   const hsbMunicipalityListRoute = appRoutes.hsbMunicipalityList(electionConfig.slug, region.slug);

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
               { href: hsbResultsRoute, label: region.region_name },
            ]}
            tabs={
               <SharedTabs
                  tabs={[
                     {
                        label: t(regionLabels.whole),
                        value: hsbResultsRoute,
                        activePatterns: [hsbResultsRoute],
                     },
                     {
                        label: t`Per gemeente`,
                        value: hsbMunicipalityListRoute,
                        activePatterns: [hsbMunicipalityListRoute],
                     },
                  ]}
               />
            }
         />
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="GEMEENTE" />
      </LayoutMain>
   );
}
