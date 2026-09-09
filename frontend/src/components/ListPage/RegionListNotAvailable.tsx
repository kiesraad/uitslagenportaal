import { Trans, useLingui } from "@lingui/react/macro";
import type { RegionCategory } from "../../api/types";
import { getRegionLabels } from "../../utils/region";
import { lowercaseFirst } from "../../utils/text";
import { InfoBox } from "../InfoBox";

type Props = {
   regionCategory: RegionCategory;
};

export function RegionListNotAvailable({ regionCategory }: Props) {
   const { t } = useLingui();
   const regionPlural = lowercaseFirst(t(getRegionLabels(regionCategory).plural));

   return (
      <div>
         <h2 className="result-unpublished">
            <Trans>De {regionPlural} zijn nog niet beschikbaar</Trans>
         </h2>
         <InfoBox disableMargin>
            <span>
               <Trans>De lijst verschijnt hier zodra de resultaten worden gepubliceerd.</Trans>
            </span>
         </InfoBox>
      </div>
   );
}
