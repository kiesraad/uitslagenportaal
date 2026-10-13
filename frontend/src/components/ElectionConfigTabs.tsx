import { useLingui } from "@lingui/react/macro";
import type { ElectionConfig } from "@/api/types";
import SharedTabs from "@/components/SharedTabs.tsx";
import { getRegionLabels } from "@/utils/region.ts";
import { appRoutes } from "@/utils/routes.ts";
import type { MessageDescriptor } from "@lingui/core";
import { msg } from "@lingui/core/macro";
import type { ElectionCategory } from "../api/types";


type Props = {
   electionConfig: Pick<ElectionConfig, "slug" | "category" | "csb_type" | "has_hsb">;
};


export type SingleCsbTab = {
   label: MessageDescriptor;
   regionSlug: string;
};

// TK and EP always have one CSB; the tab uses that name and skips the list.
const SINGLE_CSB_TABS: Partial<Record<ElectionCategory, SingleCsbTab>> = (() => ({
   TK: { label: msg`Nederland`, regionSlug: "nederland" },
   EP: { label: msg`Europees Parlement`, regionSlug: "nederland" },
}))();

export function getSingleCsbTab(category: ElectionCategory): SingleCsbTab | undefined {
   return SINGLE_CSB_TABS[category];
}


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
            // {
            //    label: singleCsb ? t(singleCsb.label) : t(getRegionLabels(electionConfig.csb_type).plural),
            //    value: singleCsb
            //       ? appRoutes.csbResults(electionConfig.slug, singleCsb.regionSlug)
            //       : appRoutes.electionConfigCSBList(electionConfig.slug),
            //    activePatterns: ["/:electionConfigSlug/csb"],
            // },
            {
               label: singleCsb ? t(singleCsb.label) : t(getRegionLabels(electionConfig.csb_type).plural),
               value: appRoutes.electionConfigCSBList(electionConfig.slug),
               activePatterns: ["/:electionConfigSlug/csb"],
            },
         ].filter((tab) => tab !== false)}
      />
   );
}
