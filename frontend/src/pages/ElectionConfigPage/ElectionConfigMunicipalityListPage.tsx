import { useLingui } from "@lingui/react/macro";
import { useParams } from "react-router";
import { Layout } from "../../components/Layout.tsx";
import { RegionList } from "../../components/ListPage/RegionList.tsx";
import { PageQueryBoundary } from "../../components/PageQueryBoundary.tsx";
import PageTop from "../../components/PageTop.tsx";
import SharedTabs from "../../components/SharedTabs.tsx";
import { useElectionConfig, useRegions } from "../../hooks/queries.ts";
import { useFormatters } from "../../utils/format.ts";
import { getRegionLabels } from "../../utils/region.ts";
import { appRoutes } from "../../utils/routes.ts";

export function ElectionConfigMunicipalityListPage() {
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const { data: electionConfig } = useElectionConfig(electionConfigSlug);
   const {
      data: regions,
      isLoading: isRegionsLoading,
      isError: isRegionsError,
      error: regionsError,
      refetch: refetchRegions,
   } = useRegions(electionConfigSlug, undefined, "GEMEENTE");

   const isLoading = isRegionsLoading;
   const isError = isRegionsError || !electionConfig || !regions;

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchRegions();
            }}
            errors={[regionsError]}
            entityLabel={t`Verkiezing`}
         />
      );
   }

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
                  href: appRoutes.electionConfigMunicipalityList(electionConfigSlug ?? ""),
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
