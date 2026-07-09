import { useParams } from 'react-router-dom'
import CandidateResultsTable from '../../components/GemeentePage/CandidateResultsTable'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import PageTop from '../../components/GemeentePage/PageTop'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsSourceBox from '../../components/GemeentePage/ResultsSourceBox'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import { Layout } from '../../components/Layout'
import { getPartyLevelResult, MUNICIPALITY_PARTY_RESULTS, POLLING_STATION_PARTY_RESULTS } from '../../data/pollingStationPartyResults'
import { POLLING_STATION_TIMELINE_STEPS } from '../../data/pollingStationTimeline'
import { getPollingStationSubtitle, getPollingStationTitle } from '../../utils/naming_helpers'
import { appRoutes } from '../../utils/routes'
import PageIndex from './PageIndex'
import { faFile } from '@fortawesome/free-regular-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

export default function PartyLevel() {
  const {
    gemeente: gemeenteParam,
    stembureau: stembureauParam,
    party: partyParam,
  } = useParams<{ gemeente: string; stembureau?: string; party: string }>()

  const gemeente = decodeURIComponent(gemeenteParam ?? '')
  const stembureau = decodeURIComponent(stembureauParam ?? '')
  const partyName = decodeURIComponent(partyParam ?? '')
  const isMunicipalityLevel = stembureauParam === undefined
  const partyResult =
    getPartyLevelResult(partyName, isMunicipalityLevel ? 'municipality' : 'polling-station') ??
    (isMunicipalityLevel ? MUNICIPALITY_PARTY_RESULTS[0] : POLLING_STATION_PARTY_RESULTS[0])
  const reportHref = appRoutes.reportError(gemeente, isMunicipalityLevel ? undefined : stembureau)
  const pageTitle = isMunicipalityLevel ? `Gemeente ${gemeente}` : getPollingStationTitle(stembureau)
  const processScope = isMunicipalityLevel ? 'gemeente' : 'stembureau'
  const processHref = isMunicipalityLevel ? appRoutes.municipalityResults(gemeente) : appRoutes.pollingStationResults(gemeente, stembureau)
  const reportsSubtitle = isMunicipalityLevel ? `Gemeente ${gemeente}` : getPollingStationSubtitle(stembureau)
  const reportsDescription = `De getallen hierboven laten zien hoe de resultaten van ${isMunicipalityLevel ? 'deze gemeente' : 'dit stembureau'} worden meegeteld in de uitslag. Ze komen uit de uitslagensoftware. Ze zijn door de gemeente overgetypt uit onderstaande documenten.`
  const reportsFiles = isMunicipalityLevel
    ? [
      {
        name: 'Proces-verbaal Na 31-2 Gemeente Lisserdam',
        icon: (
          <FontAwesomeIcon icon={faFile} />
        ),
        url: '#',
        type: 'PDF',
        size: '12 MB',
        description: 'Scan van de telresultaten van de hele gemeente.',
      },
      {
        name: 'EML_NL tellingbestand 510b',
        icon: (
          <FontAwesomeIcon icon={faFile} />
        ),
        url: '#',
        type: 'XML',
        size: '56 kB',
        description: 'Output van de optelsoftware met de resultaten van alle stembureaus en de optelling van de hele gemeente.',
      },
    ]
    : [
      {
        name: 'Corrigendum Na 14-2 bijlage 2 van stembureau 18',
        icon: (
          <FontAwesomeIcon icon={faFile} />
        ),
        url: '#',
        type: 'PDF',
        size: '5.4 MB',
        description: 'Resultaten van onderzoek naar de telresultaten van dit stembureau door het gemeentelijk stembureau.',
      },
      {
        name: 'Proces-verbaal Na 31-2 bijlage 1 van stembureau 18',
        icon: (
          <FontAwesomeIcon icon={faFile} />
        ),
        url: '#',
        type: 'PDF',
        size: '3 MB',
        description: 'Handgeschreven telresultaten. Telling per lijst en kandidaat door het gemeentelijk stembureau. Bron voor de officiele resultaten.',
      },
      {
        name: 'Proces-verbaal Na 10-2 van stembureau 18',
        type: 'PDF',
        icon: (
          <FontAwesomeIcon icon={faFile} />
        ),
        url: '#',
        size: '2.4 MB',
        description: 'Sneltelling per lijst op het stembureau (handgeschreven)',
      },
    ]

  return (
    <Layout
      title={`Telresultaten lijst ${partyResult.listNumber}`}
      description="Telresultaten per lijst en kandidaat"
    >
      <PageTop
        title={pageTitle}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
          { href: appRoutes.municipality(gemeente), label: `Gemeente ${gemeente}` },
          { href: processHref, label: isMunicipalityLevel ? 'Hele gemeente' : stembureau },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van de {processScope}</>, url: '#processen-verbaal' },
              { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h2 className="result-how-title mb-0 semibold">Telresultaten lijst {partyResult.listNumber}</h2>
            <h3 className="party-level-title mb-7">{partyResult.partyName}</h3>
            <CandidateResultsTable candidates={partyResult.candidates} totalVotes={partyResult.totalVotes} />
          </section>

          <section id="processen-verbaal">
            <ReportsWithResults
              title="Processen-verbaal met resultaten"
              subtitle={reportsSubtitle}
              description={reportsDescription}
              files={reportsFiles}
            />
          </section>

          <section id="uitleg">
            <ResultsTimeline
              title="Hoe zijn de resultaten tot stand gekomen?"
              description="In deze gemeente is gekozen voor centrale stemopneming. Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie."
              steps={POLLING_STATION_TIMELINE_STEPS}
            />
          </section>

          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>

        <div>
          <ResultsSourceBox
            description={`De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het proces-verbaal van ${isMunicipalityLevel ? 'de gemeente' : 'het stembureau'}.`}
            processHref="#processen-verbaal"
            reportHref={reportHref}
          />
        </div>
      </div>
    </Layout>
  )
}
