import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { RegionList } from "@/components/ListPage/RegionList.tsx";
import PageTop from "@/components/PageTop.tsx";
import { CSBResultsComponent } from "@/components/ResultsPage/CSBResultsComponent.tsx";
import { electionConfigQuery, regionQuery, regionsQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import type { ElectionConfig } from "../../api/types";

export function electionConfigCSBListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const electionConfig = await queryClient.query(electionConfigQueryOptions);

      const singleCSB = electionConfig.single_csb;

      if (singleCSB) {
         const regionQueryOptions = regionQuery({ ...params, regionSlug: singleCSB.slug }, "csb");
         await queryClient.query(regionQueryOptions);
         return {
            electionConfigQuery: electionConfigQueryOptions,
            regionsQuery: undefined,
            regionQuery: regionQueryOptions,
         };
      }

      const regionsQueryOptions = regionsQuery(params, electionConfig.csb_type);
      await queryClient.query(regionsQueryOptions);
      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionsQuery: regionsQueryOptions,
         regionQuery: undefined,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof electionConfigCSBListLoader>>>;

type SingleCsbResultsProps = {
   electionConfig: ElectionConfig;
   regionQuery: NonNullable<LoaderData["regionQuery"]>;
};

function SingleCsbResults({ electionConfig, regionQuery }: SingleCsbResultsProps) {
   const { data: csbRegion } = useSuspenseQuery(regionQuery);
   return <CSBResultsComponent electionConfig={electionConfig} region={csbRegion} />;
}

type CsbRegionListProps = {
   electionConfig: ElectionConfig;
   regionsQuery: NonNullable<LoaderData["regionsQuery"]>;
};

function CsbRegionList({ electionConfig, regionsQuery }: CsbRegionListProps) {
   const { data: regions } = useSuspenseQuery(regionsQuery);

   return (
      <RegionList
         electionConfig={electionConfig}
         regions={regions}
         regionCategory={electionConfig.csb_type}
         emptyPlaceholder
      />
   );
}

export function ElectionConfigCSBListPage() {
   const { electionConfigQuery, regionsQuery, regionQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);

   const electionLabel = electionConfig.label;
   const electionDay = electionConfig.date ? formatElectionDate(electionConfig.date) : "";

   return (
      <LayoutMain
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per gemeente van de ${electionLabel}.`}
      >
         <PageTop
            title={t`Telresultaten ${electionLabel}`}
            subtitle={t`Verkiezingsdag: ${electionDay}`}
            breadcrumb={[
               { href: "/", label: t`Home` },
               {
                  label: electionConfig.label,
               },
            ]}
            tabs={<ElectionConfigTabs electionConfig={electionConfig} />}
         />
         {regionQuery && <SingleCsbResults electionConfig={electionConfig} regionQuery={regionQuery} />}
         {regionsQuery && <CsbRegionList electionConfig={electionConfig} regionsQuery={regionsQuery} />}
      </LayoutMain>
   );
}
