import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";
import { uppercaseFirst } from "@/utils/text.ts";

type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "csb_type" | "single_csb" | "has_hsb">;
};

export default function ElectionConfigTabs({ electionConfig }: Props) {
   const { t } = useLingui();
   const csbLabel =
      electionConfig.csb_type === "STAAT"
         ? (electionConfig.single_csb?.region_name ?? uppercaseFirst(t(getRegionLabels("STAAT").name)))
         : t(getRegionLabels(electionConfig.csb_type).singular);

   return (
      <SharedTabs
         tabs={[
            {
               label: t(getRegionLabels("GEMEENTE").singular),
               value: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/gsb"],
            },
            electionConfig.has_hsb && {
               label: t(getRegionLabels("KIESKRING").singular),
               value: appRoutes.electionConfigHSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/hsb"],
            },
            {
               label: csbLabel,
               value: appRoutes.electionConfigCSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/csb"],
            },
         ].filter((tab) => tab !== false)}
      />
   );
}
