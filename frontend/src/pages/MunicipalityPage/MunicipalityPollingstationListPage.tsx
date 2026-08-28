import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, Navigate, useLoaderData } from "react-router";
import HtmlHead from "@/components/HtmlHead.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "@/hooks/queries.ts";
import { appRoutes } from "@/utils/routes.ts";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import MunicipalityPageLayout from "./MunicipalityPageLayout.tsx";

export function municipalityPollingstationListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionQueryOptions = regionQuery(params);
      const pollingStationsQueryOptions = regionsQuery(params, "STEMBUREAU");

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionQueryOptions),
         queryClient.ensureQueryData(pollingStationsQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionQuery: regionQueryOptions,
         pollingStationsQuery: pollingStationsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof municipalityPollingstationListLoader>>>;

export function MunicipalityPollingstationListPage() {
   const { electionConfigQuery, regionQuery, pollingStationsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   // The loader has already resolved the query, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: region } = useSuspenseQuery(regionQuery);
   const { data: pollingStations } = useSuspenseQuery(pollingStationsQuery);

   const csbSlug = region.csb_slug ?? undefined;
   // Named rather than inlined, so the catalogue carries `{regionName}` instead of `{0}`.
   const regionName = region.region_name;
   const municipalityTitle = t`Gemeente ${regionName}`;

   const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0;
   if (!hasResults) {
      return <Navigate to={appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug)} replace />;
   }

   return (
      <MunicipalityPageLayout electionConfig={electionConfig} region={region} municipalityTitle={municipalityTitle}>
         <HtmlHead title={t`Resultaten ${municipalityTitle} per stembureau`} />
         <RegionList
            electionConfig={electionConfig}
            regions={pollingStations}
            parentRegionSlug={region.slug}
            parentCsbSlug={csbSlug}
            regionTitle={municipalityTitle}
            regionCategory="STEMBUREAU"
         />
      </MunicipalityPageLayout>
   );
}
