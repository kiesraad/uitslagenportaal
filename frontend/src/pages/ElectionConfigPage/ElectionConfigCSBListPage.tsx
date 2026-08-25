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

export function ElectionConfigCSBListPage() {
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();
   const { t } = useLingui();
   const { formatElectionDate } = useFormatters();
   const {
      data: electionConfig,
      isLoading: isElectionLoading,
      isError: isElectionError,
      error: electionError,
      refetch: refetchElection,
   } = useElectionConfig(electionConfigSlug);
   const {
      data: regions,
      isLoading: isRegionsLoading,
      isError: isRegionsError,
      error: regionsError,
      refetch: refetchRegions,
   } = useRegions(electionConfigSlug, undefined, electionConfig?.csb_type);

   const isLoading = isElectionLoading || isRegionsLoading;
   const isError = isElectionError || isRegionsError || !electionConfig || !regions;

   if (isLoading || isError) {
      return (
         <PageQueryBoundary
            isLoading={isLoading}
            isError={isError}
            onRetry={() => {
               void refetchElection();
               void refetchRegions();
            }}
            errors={[electionError, regionsError]}
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
         <RegionList electionConfig={electionConfig} regions={regions} regionCategory={electionConfig.csb_type} />
      </Layout>
   );
}
