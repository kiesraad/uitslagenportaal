import { InfoBox } from './InfoBox'
import { formatDate } from '../utils/date'

type IssueReportWindowNoticeProps = {
  opensAt: string
  deadline: string
}

export default function IssueReportWindowNotice({
  opensAt,
  deadline,
}: IssueReportWindowNoticeProps) {
  return (
    <InfoBox>
      <div className="report-error-deadline">
        <h4>U heeft nog 3 dagen om een melding te maken</h4>
        <p>
          Een melding aan het centraal stembureau kan van{' '}
          {formatDate(opensAt)} tot{' '}
          {formatDate(deadline)} (uiterlijk 48 uur voor de zitting
          van het centraal stembureau). Meldingen die later binnenkomen worden niet in
          behandeling genomen.
        </p>
      </div>
    </InfoBox>
  )
}
