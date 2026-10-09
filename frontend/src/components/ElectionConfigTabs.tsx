import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { getSingleCsbTab } from "@/utils/election.ts";
import { getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "category" | "csb_type" | "has_hsb">;
};

export default function ElectionConfigTabs({ electionConfig }: Props) {
   const { t } = useLingui();
   const singleCsb = getSingleCsbTab(electionConfig.category);

   return (
      <SharedTabs
         tabs={[
            {
               label: t`Gemeente`,
               value: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/gsb"],
            },
            electionConfig.has_hsb && {
               label: t(getRegionLabels("KIESKRING").plural),
               value: appRoutes.electionConfigHSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/hsb"],
            },
            {
               label: singleCsb ? t(singleCsb.label) : t(getRegionLabels(electionConfig.csb_type).plural),
               value: singleCsb
                  ? appRoutes.csbResults(electionConfig.slug, singleCsb.regionSlug)
                  : appRoutes.electionConfigCSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/csb"],
            },
         ].filter((tab) => tab !== false)}
      />
   );
}
