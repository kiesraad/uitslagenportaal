import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, Navigate, useLoaderData, useOutletContext } from "react-router";
import HtmlHead from "@/components/HtmlHead.tsx";
import { regionsQuery } from "@/hooks/queries.ts";
import { appRoutes } from "@/utils/routes.ts";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import type { MunicipalityOutletContext } from "./MunicipalityPageLayout.tsx";

export function municipalityPollingstationListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      // The gemeente itself is loaded one level up, by the layout this page renders in.
      const pollingStationsQueryOptions = regionsQuery(params, "STEMBUREAU");
      await queryClient.ensureQueryData(pollingStationsQueryOptions);

      return {
         pollingStationsQuery: pollingStationsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof municipalityPollingstationListLoader>>>;

export function MunicipalityPollingstationListPage() {
   const { electionConfig, region, municipalityTitle } = useOutletContext<MunicipalityOutletContext>();
   const { pollingStationsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   // The loader has already resolved the query, so the data is never pending here.
   const { data: pollingStations } = useSuspenseQuery(pollingStationsQuery);

   const csbSlug = region.csb_slug ?? undefined;

   const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0;
   if (!hasResults) {
      return <Navigate to={appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug)} replace />;
   }

   return (
      <>
         <HtmlHead title={t`Resultaten ${municipalityTitle} per stembureau`} />
         <RegionList
            electionConfig={electionConfig}
            regions={pollingStations}
            parentRegionSlug={region.slug}
            parentCsbSlug={csbSlug}
            regionTitle={municipalityTitle}
            regionCategory="STEMBUREAU"
         />
      </>
   );
}
