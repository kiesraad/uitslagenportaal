import { Trans } from "@lingui/react/macro";
import { InfoBox } from "../../components/InfoBox";

type Props = {
   regionLabel: string;
};
export default function ResultsNotPublished({ regionLabel }: Props) {
   return (
      <div>
         <h2 className="result-unpublished">
            <Trans>De telresultaten van {regionLabel} zijn nog niet gepubliceerd</Trans>
         </h2>
         <InfoBox disableMargin>
            <span>
               <Trans>
                  De telresultaten en processen-verbaal van {regionLabel} zijn hier te zien zodra de {regionLabel} ze
                  publiceert.
               </Trans>
            </span>
         </InfoBox>
      </div>
   );
}
