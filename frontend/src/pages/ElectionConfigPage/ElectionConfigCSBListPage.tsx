import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { RegionList } from "@/components/ListPage/RegionList.tsx";
import PageTop from "@/components/PageTop.tsx";
import { electionConfigQuery, regionsQuery, regionQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";
import { CSBResultsComponent } from "@/components/ResultsPage/CSBResultsComponent.tsx";
import { getSingleCsbTab } from "@/utils/election.ts";
import type { ElectionConfig } from "../../api/types";


export function electionConfigCSBListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const electionConfig = await queryClient.query(electionConfigQueryOptions);

      const regionsQueryOptions = regionsQuery(params, electionConfig?.csb_type);
      const singleCSB = getSingleCsbTab(electionConfig.category) 

      const regionQueryOptions = singleCSB
         ? regionQuery({ ...params, regionSlug: singleCSB.regionSlug }, "csb")
         : undefined;
      await queryClient.query(regionsQueryOptions);
      if (regionQueryOptions) {
         await queryClient.query(regionQueryOptions);
      }
      

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionsQuery: regionsQueryOptions,
         regionQuery: regionQueryOptions,
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



export function ElectionConfigCSBListPage() {
   const { electionConfigQuery, regionsQuery, regionQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: regions } = useSuspenseQuery(regionsQuery);

   const singleCSB = getSingleCsbTab(electionConfig.category) 
   console.log('singleCSB ', singleCSB)


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
         {regionQuery ? (
            <SingleCsbResults electionConfig={electionConfig} regionQuery={regionQuery} />
         ) : (
            <RegionList
               electionConfig={electionConfig}
               regions={regions}
               regionCategory={electionConfig.csb_type}
               emptyPlaceholder
            />
         )}
      </LayoutMain>
   );
}
