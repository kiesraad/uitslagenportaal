import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { RegionList } from "@/components/ListPage/RegionList.tsx";
import PageTop from "@/components/PageTop.tsx";
import { electionConfigQuery, regionsQuery } from "@/hooks/queries.ts";
import { useFormatters } from "@/utils/format.ts";

export function electionConfigCSBListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const electionConfig = await queryClient.query(electionConfigQueryOptions);

      const regionsQueryOptions = regionsQuery(params, electionConfig?.csb_type);
      await queryClient.query(regionsQueryOptions);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionsQuery: regionsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof electionConfigCSBListLoader>>>;

export function ElectionConfigCSBListPage() {
   const { electionConfigQuery, regionsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: regions } = useSuspenseQuery(regionsQuery);

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
         <RegionList
            electionConfig={electionConfig}
            regions={regions}
            regionCategory={electionConfig.csb_type}
            emptyPlaceholder
         />
      </LayoutMain>
   );
}
