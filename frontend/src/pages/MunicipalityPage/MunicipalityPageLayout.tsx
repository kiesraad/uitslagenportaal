import { useLingui } from "@lingui/react/macro";
import type { PropsWithChildren } from "react";
import type { ElectionConfig, Region } from "@/api/types.ts";
import { LayoutMain } from "@/components/LayoutMain.tsx";
import PageTop from "@/components/PageTop.tsx";
import SharedTabs from "@/components/SharedTabs.tsx";
import { useFormatters } from "@/utils/format.ts";
import { getCsbCrumb } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

type MunicipalityPageLayoutProps = PropsWithChildren<{
   electionConfig: ElectionConfig;
   region: Region;
   municipalityTitle: string;
}>;

export default function MunicipalityPageLayout({
   children,
   electionConfig,
   region,
   municipalityTitle,
}: MunicipalityPageLayoutProps) {
   const { t } = useLingui();
   const { formatDate } = useFormatters();

   const csbSlug = region.csb_slug ?? undefined;
   const municipalityPollingstationListRoute = appRoutes.municipalityPollingstationList(
      electionConfig.slug,
      region.slug,
      csbSlug,
   );
   const municipalityResultsRoute = appRoutes.municipalityResults(electionConfig.slug, region.slug, csbSlug);

   const hasResults = Array.isArray(region.vote_counts) && region.vote_counts.length > 0;
   // No publication date until the region's results have been imported; the line is then omitted.
   const publishedAt = region.results_available_at ? formatDate(region.results_available_at) : null;

   return (
      <LayoutMain>
         <PageTop
            title={municipalityTitle}
            subtitle={publishedAt ? t`Geplaatst op: ${publishedAt}` : undefined}
            breadcrumb={[
               { href: appRoutes.home(), label: t`Home` },
               {
                  href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                  label: electionConfig.label,
               },
               getCsbCrumb(region, electionConfig.slug),
               { href: municipalityPollingstationListRoute, label: municipalityTitle },
            ]}
            tabs={
               hasResults && (
                  <SharedTabs
                     tabs={[
                        {
                           label: t`Resultaten per stembureau`,
                           value: municipalityPollingstationListRoute,
                           activePatterns: [municipalityPollingstationListRoute],
                        },
                        {
                           label: t`Hele gemeente`,
                           value: municipalityResultsRoute,
                           activePatterns: [municipalityResultsRoute],
                        },
                     ]}
                  />
               )
            }
         />
         {children}
      </LayoutMain>
   );
}
