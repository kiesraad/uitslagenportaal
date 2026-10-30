import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { useElectionConfigs } from "@/hooks/queries.ts";
import { getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";

type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "csb_type" | "single_csb" | "has_hsb">;
};

export default function ElectionConfigTabs({ electionConfig }: Props) {
   const { t } = useLingui();
   const singleCsb = electionConfig.single_csb;
   // With a single election the homepage shows the timeline instead.
   const { data: electionConfigs } = useElectionConfigs();
   const showTimeline = (electionConfigs?.length ?? 0) > 1;

   return (
      <SharedTabs
         tabs={[
            showTimeline && {
               label: t`Van stem tot uitslag`,
               value: appRoutes.electionConfigTimeline(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/van-stem-tot-uitslag"],
            },
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
               label: singleCsb ? singleCsb.region_name : t(getRegionLabels(electionConfig.csb_type).plural),
               value: appRoutes.electionConfigCSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/csb"],
            },
         ].filter((tab) => tab !== false)}
      />
   );
}
