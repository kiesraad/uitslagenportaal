import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useParams } from "react-router";
import ElectionConfigTabs from "@/components/ElectionConfigTabs.tsx";
import { electionConfigQuery, regionsQuery } from "@/hooks/queries.ts";
import { LayoutMain } from "../../components/LayoutMain.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import PageTop from "../../components/PageTop.tsx";
import { useFormatters } from "../../utils/format.ts";

export async function loadElectionConfigMunicipalityList(
   client: QueryClient,
   { params }: Pick<LoaderFunctionArgs, "params">,
) {
   await Promise.all([
      client.query(electionConfigQuery(params.electionConfigSlug)),
      client.query(regionsQuery(params, "GEMEENTE")),
   ]);
}

export default function ElectionConfigMunicipalityListPage() {
   const params = useParams();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery(params.electionConfigSlug));
   const { data: regions } = useSuspenseQuery(regionsQuery(params, "GEMEENTE"));

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
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="GEMEENTE" emptyPlaceholder />
      </LayoutMain>
   );
}
