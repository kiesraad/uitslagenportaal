import { useLingui } from "@lingui/react/macro";
import { type QueryClient, useSuspenseQuery } from "@tanstack/react-query";
import { type LoaderFunctionArgs, useLoaderData } from "react-router";
import { electionConfigQuery, regionsQuery } from "@/hooks/queries.ts";
import { Layout } from "../../components/Layout.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function electionConfigMunicipalityListLoader(queryClient: QueryClient) {
   return async ({ params }: LoaderFunctionArgs) => {
      const electionConfigQueryOptions = electionConfigQuery(params.electionConfigSlug);
      const regionsQueryOptions = regionsQuery(params, "GEMEENTE");

      await Promise.all([
         queryClient.ensureQueryData(electionConfigQueryOptions),
         queryClient.ensureQueryData(regionsQueryOptions),
      ]);

      return {
         electionConfigQuery: electionConfigQueryOptions,
         regionsQuery: regionsQueryOptions,
      };
   };
}

type LoaderData = Awaited<ReturnType<ReturnType<typeof electionConfigMunicipalityListLoader>>>;

export function ElectionConfigMunicipalityListPage() {
   const { electionConfigQuery, regionsQuery } = useLoaderData<LoaderData>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   // The loader has already resolved both queries, so the data is never pending here.
   const { data: electionConfig } = useSuspenseQuery(electionConfigQuery);
   const { data: regions } = useSuspenseQuery(regionsQuery);

   const electionLabel = electionConfig.label;
   const electionDay = electionConfig.date ? formatElectionDate(electionConfig.date) : "";

   return (
      <Layout
         title={t`Telresultaten ${electionLabel}`}
         description={t`Bekijk de telresultaten per gemeente van de ${electionLabel}.`}
      >
         <PageTop
            title={t`Telresultaten ${electionLabel}`}
            subtitle={t`Verkiezingsdag: ${electionDay}`}
            breadcrumb={[
               { href: "/", label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
            ]}
            tabs={
               <SharedTabs
                  tabs={[
                     {
                        label: t`Gemeente`,
                        value: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                        activePatterns: ["/:electionConfigSlug/gsb"],
                     },
                     {
                        label: t(getRegionLabels(electionConfig.csb_type).plural),
                        value: appRoutes.electionConfigCSBList(electionConfig.slug),
                        activePatterns: ["/:electionConfigSlug/csb"],
                     },
                  ]}
               />
            }
         />
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory="GEMEENTE" />
      </Layout>
   );
}
