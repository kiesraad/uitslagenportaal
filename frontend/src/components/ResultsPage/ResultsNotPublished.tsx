import {Trans, useLingui} from "@lingui/react/macro";
import {lowercaseFirst} from "@/utils/text.ts";
import type {RegionCategory} from "../../api/types";
import {InfoBox} from "../../components/InfoBox";
import {getRegionLabels, regionWithName} from "../../utils/region";

type Props = {
   regionName: string;
   regionCategory: RegionCategory;
};

export default function ResultsNotPublished({regionName, regionCategory}: Props) {
   const {t} = useLingui();

   const regionLabels = getRegionLabels(regionCategory);
   const regionLabel = t(regionWithName(regionCategory, regionName));
   const csbName = lowercaseFirst(t(regionLabels?.csbName ?? regionLabels.withArticle));

   return (
      <div>
         <h2 className="result-unpublished">
            <Trans>De telresultaten van {regionLabel} zijn nog niet gepubliceerd</Trans>
         </h2>
         <InfoBox disableMargin>
            <span>
               <Trans>
                  De telresultaten en processen-verbaal van {regionLabel} zijn hier te zien zodra {csbName} ze
                  publiceert.
               </Trans>
            </span>
         </InfoBox>
      </div>
   );
}
