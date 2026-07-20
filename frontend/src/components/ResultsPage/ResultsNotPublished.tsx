import { InfoBox } from '../../components/InfoBox'
import type { ElectionConfig } from '../../api/types'

type Props = {
    electionConfig?: ElectionConfig;
}
export default function ResultsNotPublished({ region }: Props) {
    return (
        <>
            <h2 className="result-unpublished">
                De telresultaten van Kieskring {'kieskringNr'} zijn nog niet gepubliceerd
            </h2>

            <InfoBox>
                <span>
                    De telresultaten en processen-verbaal van de gemeente {'kieskring'} zijn hier
                    te zien zodra de gemeente ze publiceert.
                </span>
            </InfoBox>

        </>
    )
}
