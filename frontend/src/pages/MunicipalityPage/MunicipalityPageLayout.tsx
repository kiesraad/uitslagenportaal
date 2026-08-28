import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, Outlet, useLoaderData } from "react-router";
import type { ElectionConfig, Region } from "@/api/types.ts";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import PageTop from "@/components/PageTop.tsx";
import SharedTabs from "@/components/SharedTabs.tsx";
import { electionConfigQuery, regionQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import { getCsbCrumb } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

/** The gemeente the whole `gsb/:regionSlug/csb/:csbSlug` subtree is about. */
export function municipalityLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
      };
   };
}

export type MunicipalityLoaderData = Awaited<ReturnType<ReturnType<typeof municipalityLoader>>>;

export type MunicipalityOutletContext = {
   electionConfig: ElectionConfig;
   region: Region;
   municipalityTitle: string;
};

export default function MunicipalityPageLayout() {
   const { electionConfigQuery, regionQuery } = useLoaderData<MunicipalityLoaderData>();
   const { t } = useLingui();
   const { formatDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);

   const csbSlug = region.csb_slug ?? undefined;
   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfig.slug,
      region.slug,
      csbSlug,
   );
   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug);

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
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               getCsbCrumb(region, electionConfig.slug),
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
         <Outlet context={{ electionConfig, region, municipalityTitle } satisfies MunicipalityOutletContext} />
      </LayoutMain>
   );
}
