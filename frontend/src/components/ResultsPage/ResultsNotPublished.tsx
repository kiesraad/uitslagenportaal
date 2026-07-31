import { InfoBox } from '../../components/InfoBox'

type Props = {
    regionLabel: string;
}
export default function ResultsNotPublished({ regionLabel }: Props) {
    return (
        <div>
            <h2 className="result-unpublished">
                {`De telresultaten van ${regionLabel} zijn nog niet gepubliceerd`}
            </h2>
            <InfoBox disableMargin>
                <span>
                    {`De telresultaten en processen-verbaal van ${regionLabel} 
                    zijn hier te zien zodra de ${regionLabel} ze publiceert.`}
                </span>
            </InfoBox>
        </div>
    )
}
