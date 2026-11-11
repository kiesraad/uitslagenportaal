import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { CSBResultsComponent } from "@/components/ResultsPage/CSBResultsComponent.tsx";
import { queryClient } from "@/queryClient.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";
import type { Route } from "./+types/CSBResultsPage";

export async function loadCSBResults(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "csb")),
   ]);
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadCSBResults(queryClient, args);

export default function CSBResultsPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "csb"));

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
