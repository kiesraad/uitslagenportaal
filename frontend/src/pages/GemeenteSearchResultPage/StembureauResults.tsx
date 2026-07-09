import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import VOTES_CAST_POLLING_STATION from '../../assets/votes_cast_polling_station.json'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import PageTop from '../../components/GemeentePage/PageTop'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsSourceBox from '../../components/GemeentePage/ResultsSourceBox'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import VotesList from '../../components/GemeentePage/VotesList'
import VotesResume from '../../components/GemeentePage/VotesResume'
import { Layout } from '../../components/Layout'
import { POLLING_STATION_TIMELINE_STEPS } from '../../data/pollingStationTimeline'
import { getPollingStationSubtitle, getPollingStationTitle } from '../../utils/naming_helpers'
import { appRoutes } from '../../utils/routes'
import PageIndex from './PageIndex'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFile } from '@fortawesome/free-solid-svg-icons'

const DEFAULT_GEMEENTE = 'Lisserdam'

export default function StembureauResults() {
  const { gemeente: gemeenteParam, stembureau: stembureauParam } = useParams<{ gemeente?: string; stembureau: string }>()
  const stembureau = decodeURIComponent(stembureauParam ?? '')
  const gemeente = decodeURIComponent(gemeenteParam ?? DEFAULT_GEMEENTE)
  const reportHref = appRoutes.reportError(gemeente, stembureau)

  const pollingStationVotes = useMemo(
    () =>
      VOTES_CAST_POLLING_STATION.map((vote) => ({
        ...vote,
        url: appRoutes.partyLevel(gemeente, stembureau, vote.name),
      })),
    [gemeente, stembureau],
  )

  return (
    <Layout
      title="Telresultaten stembureau"
      description="Telresultaten stembureau"
    >
      <PageTop
        title={getPollingStationTitle(stembureau)}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
          { href: appRoutes.municipality(gemeente), label: `Gemeente ${gemeente}` },
          { href: appRoutes.pollingStationResults(gemeente, stembureau), label: stembureau },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van het stembureau</>, url: '#processen-verbaal' },
              { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.</p>
          </section>

          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume
              votes={[
                { name: 'Stempassen', count: 855 },
                { name: 'Volmachtbewijzen', count: 15 },
                { name: 'Kiezerspassen', count: 4 },
                { name: 'Toegelaten kiezers', count: 874, bold: true },
              ]}
            />
          </section>

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
            <VotesList votes={pollingStationVotes} />
          </section>

          <VotesResume
            votes={[
              { name: 'Totaal stemmen op kandidaten', count: 867, bold: true },
              { name: 'Blanco stemmen', count: 2 },
              { name: 'Ongeldige stemmen', count: 4 },
              { name: 'Totaal uitgebrachte stemmen', count: 873, bold: true },
            ]}
          />

          <section id="processen-verbaal">
            <ReportsWithResults
              title="Processen-verbaal met resultaten"
              subtitle={getPollingStationSubtitle(stembureau)}
              description="De getallen hierboven laten zien hoe de resultaten van dit stembureau worden meegeteld in de uitslag. Ze komen uit de uitslagensoftware. Ze zijn door de gemeente overgetypt uit onderstaande documenten."
              files={[
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
                  description: 'Handgeschreven telresultaten. Sneltelling per lijst op het stembureau, geen officiele resultaten.',
                },
              ]}
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
            description="De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het proces-verbaal dat gemaakt is na het tellen van de stemmen."
            processHref="#processen-verbaal"
            reportHref={reportHref}
          />
        </div>
      </div>
    </Layout>
  )
}
