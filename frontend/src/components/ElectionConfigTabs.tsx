import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { electionHasHsb, getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "csb_type" | "single_csb" | "has_hsb">;
};

export default function ElectionConfigTabs({ electionConfig }: Props) {
   const { t } = useLingui();
   const csbLabel =
      electionConfig.csb_type === "STAAT"
         ? (electionConfig.single_csb?.region_name ?? t({ message: "Nederland", context: "tab" }))
         : t(getRegionLabels(electionConfig.csb_type).plural);

   return (
      <SharedTabs
         tabs={[
            {
               label: t(getRegionLabels("GEMEENTE").plural),
               value: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/gsb"],
            },
            electionHasHsb(electionConfig) && {
               label: t(getRegionLabels("KIESKRING").plural),
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
