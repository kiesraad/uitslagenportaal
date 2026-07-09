import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import VOTES_CAST_MUNICIPALITY from '../../assets/votes_cast_municipality.json'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import PageTop from '../../components/GemeentePage/PageTop'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsSourceBox from '../../components/GemeentePage/ResultsSourceBox'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import SharedTabs from '../../components/GemeentePage/SharedTabs'
import VotesList from '../../components/GemeentePage/VotesList'
import VotesResume from '../../components/GemeentePage/VotesResume'
import { Layout } from '../../components/Layout'
import { appRoutes } from '../../utils/routes'
import PageIndex from './PageIndex'
import type { Step } from '../../components/Timeline'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFile, faFileArchive, faFolder } from '@fortawesome/free-regular-svg-icons'
import { faTable } from '@fortawesome/free-solid-svg-icons'

const STEPS: Step[] = [
  {
    state: 'in-progress',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: 'De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht moeten worden? Als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld, en wordt de uitslag vastgesteld.',
  },
  {
    state: 'done',
    title: 'Optelling Kieskring 23',
    date: '10 december op hoofdstembureau van de kieskring in Zwijgendam',
    body: 'De resultaten van alle gemeenten in kieskring 23 worden op het hoofdstembureau gecontroleerd en bij elkaar opgeteld.',
  },
  {
    state: 'done',
    title: 'Gemeentelijke optelling',
    date: '9 december op centrale tellocatie in gemeente Lisserdam',
    body: 'De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag.',
  },
  {
    state: 'done',
    title: 'Telling per lijst en kandidaat',
    date: '9 december op centrale tellocatie in gemeente Lisserdam',
    body: 'Het gemeentelijk stembureau telt per stembureau alle stembiljetten op kandidaatsniveau: voor welke kandidaten per partij de stemmen precies zijn uitgebracht. **Deze telling is de basis van de officiele uitslag.**',
  },
  {
    state: 'done',
    title: 'Sneltelling in het stembureau',
    date: '8 december na 21:00 in lokale stembureaus',
    body: 'Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus. **Dit is niet de officiele uitslag.**',
  },
]

export default function HeleGemeenteResults() {
  const { gemeente: gemeenteParam } = useParams<{ gemeente: string }>()
  const gemeente = decodeURIComponent(gemeenteParam ?? '')
  const reportHref = appRoutes.reportError(gemeente)
  const municipalityRoute = appRoutes.municipality(gemeente)
  const municipalityResultsRoute = appRoutes.municipalityResults(gemeente)
  const municipalityVotes = useMemo(
    () =>
      VOTES_CAST_MUNICIPALITY.map((vote) => ({
        ...vote,
        url: appRoutes.municipalityPartyLevel(gemeente, vote.name),
      })),
    [gemeente],
  )

  return (
    <Layout
      title="Gemeente resultaten"
      description="Gemeente resultaten"
    >
      <PageTop
        title={`Gemeente ${gemeente}`}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
          { href: municipalityRoute, label: `Gemeente ${gemeente}` },
        ]}
        tabs={
          <SharedTabs
            tabs={[
              {
                label: 'Resultaten per stembureau',
                value: municipalityRoute,
                activePatterns: [municipalityRoute, `${municipalityRoute}/stembureau/resultaten/*`],
              },
              {
                label: 'Hele gemeente',
                value: municipalityResultsRoute,
                activePatterns: [municipalityResultsRoute],
              },
            ]}
          />
        }
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van de gemeente</>, url: '#processen-verbaal' },
              { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>Het gemeentelijk stembureau heeft de telresultaten van alle stembureaus in {gemeente} gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het proces-verbaal van de gemeente.</p>
          </section>

          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume
              votes={[
                { name: 'Stempassen', count: 18539 },
                { name: 'Volmachtbewijzen', count: 162 },
                { name: 'Kiezerspassen', count: 39 },
                { name: 'Toegelaten kiezers', count: 18740, bold: true },
              ]}
            />
          </section>

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">
              Klik op een lijst om de stemmen per kandidaat te zien. Weten hoe er in uw stembureau is gestemd? Bekijk de{' '}
              <Link to={municipalityRoute}>resultaten per stembureau</Link>.
            </p>
            <VotesList votes={municipalityVotes} />
          </section>

          <VotesResume
            votes={[
              { name: 'Totaal stemmen op kandidaten', count: 18703, bold: true },
              { name: 'Blanco stemmen', count: 21 },
              { name: 'Ongeldige stemmen', count: 13 },
              { name: 'Totaal uitgebrachte stemmen', count: 18739, bold: true },
            ]}
          />

          <section id="processen-verbaal">
            <ReportsWithResults
              title="Processen-verbaal met resultaten"
              description="Onderstaande documenten bevatten de laatste telresultaten van de gemeente, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
              files={[
                {
                  name: 'Proces-verbaal Na 31-2 Gemeente Lisserdam',
                  icon: (
                    <FontAwesomeIcon icon={faFile} />
                  ),
                  url: '#',
                  type: 'PDF',
                  size: '12 MB',
                  description: 'Scan van de telresultaten van de hele gemeente',
                },
                {
                  name: 'EML_NL tellingbestand 510b',
                  type: 'XML',
                  icon: (
                    <FontAwesomeIcon icon={faFolder} />
                  ),
                  url: '#',
                  size: '56 kB',
                  description: 'Output van de optelsoftware, bevat de resultaten van alle stembureaus en de optelling van de hele gemeente. Bron van de informatie op deze pagina.',
                },
                {
                  name: 'Excel bestand',
                  type: 'XLSX',
                  icon: (
                    <FontAwesomeIcon icon={faTable} />
                  ),
                  url: '#',
                  size: '223 kB',
                  description: 'Toegankelijke versie van digitaal tellingbestand 510b',
                },
                {
                  name: 'Processen-verbaal van alle stembureaus',
                  type: 'ZIP',
                  icon: (
                    <FontAwesomeIcon icon={faFileArchive} />
                  ),
                  url: '#',
                  size: '48 MB',
                  description: 'Handgeschreven verslagen van alle 29 stembureaus',
                },
              ]}
            />
          </section>

          <section id="uitleg">
            <ResultsTimeline
              title="Hoe zijn de resultaten tot stand gekomen?"
              description="In deze gemeente is gekozen voor centrale stemopneming. Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie."
              steps={STEPS}
            />
          </section>

          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>

        <div>
          <ResultsSourceBox
            description="De telresultaten op deze pagina komen uit de uitslagensoftware. Dat zijn de resultaten die meetellen in de officiele uitslag. De gemeente heeft de resultaten gecontroleerd en vastgelegd in onderstaand proces-verbaal."
            processHref="#processen-verbaal"
            reportHref={reportHref}
          />
        </div>
      </div>
    </Layout>
  )
}
