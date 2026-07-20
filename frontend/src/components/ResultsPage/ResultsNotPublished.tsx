import { InfoBox } from '../../components/InfoBox'
import type { Region } from '../../api/types'

type Props = {
    region: Region;
}
export default function ResultsNotPublished({ region }: Props) {
    return (
        <>
            <h2 className="result-unpublished">
                {`De telresultaten van ${region.region_category.toLowerCase()} ${region.region_name} zijn nog niet gepubliceerd`}
            </h2>

            <InfoBox>
                <span>
                    {`De telresultaten en processen-verbaal van de gemeente ${region.region_category} ${region.region_name} 
                    zijn hier te zien zodra de ${region.region_category} ze publiceert.`}
                </span>
            </InfoBox>

        </>
    )
}
