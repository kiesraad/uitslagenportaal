import { Trans, useLingui } from "@lingui/react/macro";
import type { RegionCategory } from "../../api/types";
import { InfoBox } from "../../components/InfoBox";
import { getRegionLabels } from "../../utils/region";

type Props = {
   regionName: string;
   regionCategory: RegionCategory;
};

export default function ResultsNotPublished({ regionName, regionCategory }: Props) {
   const { t } = useLingui();
   if (regionCategory === "STAAT") {
      return (
         <div>
            <h2 className="result-unpublished">
               <Trans>De telresultaten van Nederland zijn nog niet gepubliceerd</Trans>
            </h2>
            <InfoBox disableMargin>
               <span>
                  <Trans>
                     De telresultaten en processen-verbaal van Nederland zijn hier te zien zodra de Kiesraad ze
                     publiceert.
                  </Trans>
               </span>
            </InfoBox>
         </div>
      );
   }

   const regionLabel = `${t(getRegionLabels(regionCategory).withArticle)} ${regionName}`;
   return (
      <div>
         <h2 className="result-unpublished">
            <Trans>De telresultaten van {regionLabel} zijn nog niet gepubliceerd</Trans>
         </h2>
         <InfoBox disableMargin>
            <span>
               <Trans>
                  De telresultaten en processen-verbaal van {regionLabel} zijn hier te zien zodra {regionLabel} ze
                  publiceert.
               </Trans>
            </span>
         </InfoBox>
      </div>
   );
}
