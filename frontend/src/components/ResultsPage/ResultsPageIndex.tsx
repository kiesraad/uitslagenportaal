import PageIndex from '../PageIndex'

type ResultsPageIndexVariant = 'full' | 'party'

type Props = {
  variant?: ResultsPageIndexVariant
}

const telresultatenLink = {
  label: (
    <>
      <span className="font-semibold">Telresultaten</span> zoals ze meetellen in de officiele uitslag
    </>
  ),
  url: '#telresultaten',
}

const timelineLink = {
  label: (
    <>
      <span className="font-semibold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen
    </>
  ),
  url: '#results-timeline',
}

const issueReportLink = {
  label: <span className="font-semibold">Hoe u een fout kunt melden</span>,
  url: '#fout-melden',
}

export default function ResultsPageIndex({ variant = 'full' }: Props) {
  const links =
    variant === 'party'
      ? [telresultatenLink, issueReportLink]
      : [telresultatenLink, timelineLink, issueReportLink]

  return <PageIndex links={links} />
}
