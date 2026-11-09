import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import { ApiError } from "@/api/client.ts";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import { RegionList } from "@/components/ListPage/RegionList.tsx";
import PageTop from "@/components/PageTop.tsx";
import { electionConfigQuery, regionsQuery } from "@/hooks/queries.ts";
import { queryClient } from "@/queryClient.ts";
import { useFormatters } from "@/utils/format.ts";
import type { Route } from "./+types/ElectionConfigHSBListPage";

export async function loadElectionConfigHSBList(client: QueryClient, { params }: Pick<LoaderFunctionArgs, "params">) {
   const [electionConfig] = await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionsQuery(params, "KIESKRING")),
   ]);

   if (!electionConfig.has_hsb) {
      throw new ApiError("Election has no HSBs", 404);
   }
}

export const clientLoader = (args: Route.ClientLoaderArgs) => loadElectionConfigHSBList(queryClient, args);

export default function ElectionConfigHSBListPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: regions } = useSuspenseQuery(regionsQuery(params, "KIESKRING"));

   const electionLabel = electionConfig.label;
   const electionDay = electionConfig.date ? formatElectionDate(electionConfig.date) : "";

   return (
      <LayoutMain
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per kieskring van de ${electionLabel}.`}
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
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="KIESKRING" emptyPlaceholder />
      </LayoutMain>
   );
}
