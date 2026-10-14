import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "csb_type" | "single_csb" | "has_hsb">;
};

export default function ElectionConfigTabs({ electionConfig }: Props) {
   const { t } = useLingui();
   const singleCsb = electionConfig.single_csb;

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
            // {
            //    label: singleCsb ? t(singleCsb.label) : t(getRegionLabels(electionConfig.csb_type).plural),
            //    value: singleCsb
            //       ? appRoutes.csbResults(electionConfig.slug, singleCsb.regionSlug)
            //       : appRoutes.electionConfigCSBList(electionConfig.slug),
            //    activePatterns: ["/:electionConfigSlug/csb"],
            // },
            {
               label: singleCsb ? singleCsb.region_name : t(getRegionLabels(electionConfig.csb_type).plural),
               value: appRoutes.electionConfigCSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/csb"],
            },
         ].filter((tab) => tab !== false)}
      />
   );
}
