import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, Navigate, useParams } from "react-router";
import HtmlHead from "@/components/HtmlHead.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "@/hooks/queries.ts";
import { appRoutes } from "@/utils/routes.ts";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import MunicipalityPageLayout from "./MunicipalityPageLayout.tsx";

export async function loadMunicipalityPollingstationList(
   client: QueryClient,
   { params }: Pick<LoaderFunctionArgs, "params">,
) {
   await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionQuery(params, "gsb")),
      client.query(regionsQuery(params, "STEMBUREAU")),
   ]);
}

export default function MunicipalityPollingstationListPage() {
   const params = useParams();
   const { t } = useLingui();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: region } = useSuspenseQuery(regionQuery(params, "gsb"));
   const { data: pollingStations } = useSuspenseQuery(regionsQuery(params, "STEMBUREAU"));

   const csbSlug = region.csb?.slug;
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
