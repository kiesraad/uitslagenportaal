import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import SharedTabs from '../../components/GemeentePage/SharedTabs'
import { appRoutes } from '../../utils/routes'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import PageIndex from '../GemeenteSearchResultPage/PageIndex'
import VotesResume from '../../components/GemeentePage/VotesResume'
import VotesList from '../../components/GemeentePage/VotesList'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import ResultsSourceBox from '../../components/GemeentePage/ResultsSourceBox'
import type { Step } from '../../components/Timeline'
import { faFile, faFolder } from '@fortawesome/free-regular-svg-icons'
import { faTable } from '@fortawesome/free-solid-svg-icons'
import VOTES_CAST_KIESKRING from '../../assets/votes_cast_kieskring.json'
import KIESKRINGEN from '../../assets/kieskringen.json'

const STEPS: Step[] = [
  {
    state: 'in-progress',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: `De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht moeten worden? Als alles klopt worden de resultaten van alle gemeenten bij elkaar opgeteld, en wordt de uitslag vastgesteld.

Bekijk de [resultaten van heel Nederland](#) → `,
  },
  {
    state: 'done',
    title: 'Optelling Kieskring 7',
    date: '10 december op hoofdstembureau van de kieskring in Arnhem',
    body: 'De resultaten van alle gemeenten in Kieskring 7 worden op het hoofdstembureau gecontroleerd bij elkaar opgeteld.',
    files: [
      {
        name: 'Proces-verbaal Model O 7, P1f-1 Kieskring 7',
        url: '#',
        type: 'PDF',
        size: '12 MB',
        description: 'Scan van de telresultaten en zetelverdeling van Nederland',
      },
      {
        name: 'EML_NL tellingbestand 510c',
        url: '#',
        type: 'xml',
        size: '56 kB',
        description: 'EML_NL tellingbestand 510c',
      },
    ],
  },
  {
    state: 'done',
    title: 'Optelling per gemeente',
    date: '9 december op centrale tellocatie in elke gemeente',
    body: `De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag.

Bekijk de [resultaten van de gemeente in kieskring 7](#) → `,
  },
  {
    state: 'done',
    title: 'Telling in de stembureaus',
    date: '8 december na 21:00 in lokale stembureaus',
    body: 'Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus en wordt gepubliceerd door media en persbureaus. **Het is dus nog niet de officiële uitslag van de Kiesraad.**',
  },
]

type Props = {
  kieskring: string
}

export default function ResultsAvailable({ kieskring }: Props) {
  const kieskringRoutes = appRoutes.kieskring(kieskring)
  const reportHref = appRoutes.reportError(kieskring)

  const kieskringNr = KIESKRINGEN.find(kring => kring.name === kieskring)?.kieskring_nr;

  return (
    <Layout
      title={`Resultaten Kieskring ${kieskringNr}`}
      description={`Resultaten Kieskring ${kieskringNr}`}
    >
      <PageTop
        title={`Kieskring ${kieskringNr} - ${kieskring}`}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
          { href: kieskringRoutes, label: `Kieskring` },
        ]}
        tabs={
          <SharedTabs
            tabs={[
              { label: 'Hele kieskring', value: appRoutes.kieskring(kieskring), activePatterns: ['/kieskring', '/kieskring/*'] },
              { label: 'Per gemeente', value: appRoutes.kieskringGemeente(kieskring), activePatterns: ['/kieskring/*/gemeente'] }
            ]}
          />
        }
      />

      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="bold">Processen-verbaal</span> de officiële documenten van de kieskring</>, url: '#processen-verbaal' },
              { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>Het centraal stembureau heeft de telresultaten van alle gemeenten en kieskringen gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het proces-verbaal van het centraal stembureau.</p>
          </section>

          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume
              votes={[
                { name: 'Stempassen', count: 850534 },
                { name: 'Volmachtbewijzen', count: 2512 },
                { name: 'Kiezerspassen', count: 438 },
                { name: 'Toegelaten kiezers', count: 851223, bold: true },
              ]}
            />
          </section>

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">
              Klik op een lijst om de stemmen per kandidaat te zien
            </p>
            <VotesList votes={VOTES_CAST_KIESKRING} />
          </section>

          <VotesResume
            votes={[
              { name: 'Totaal stemmen op kandidaten', count: 847617, bold: true },
              { name: 'Blanco stemmen', count: 1396 },
              { name: 'Ongeldige stemmen', count: 2213 },
              { name: 'Totaal uitgebrachte stemmen', count: 851226, bold: true },
            ]}
          />

          <IssueNotice reportHref={reportHref} id="fout-melden" />

          <section id="processen-verbaal">
            <ReportsWithResults
              title="Processen-verbaal met resultaten"
              description="Onderstaande documenten bevatten de laatste telresultaten van de kieskring, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
              files={[
                {
                  name: `Proces-verbaal Model O 7 Kieskring ${kieskringNr}`,
                  icon: (
                    <FontAwesomeIcon icon={faFile} />
                  ),
                  url: '#',
                  type: 'PDF',
                  size: '12 MB',
                  description: `Scan van de telresultaten van de hele kieskring ${kieskring}`,
                },
                {
                  name: 'EML_NL tellingbestand 510c',
                  type: 'XML',
                  icon: (
                    <FontAwesomeIcon icon={faFolder} />
                  ),
                  url: '#',
                  size: '156 kB',
                  description: 'Output van de optelsoftware, bevat de resultaten van alle gemeenten en de optelling van de hele kieskring. Bron van de informatie op deze pagina.',
                },
                {
                  name: 'Excel bestand',
                  type: 'XLSX',
                  icon: (
                    <FontAwesomeIcon icon={faTable} />
                  ),
                  url: '#',
                  size: '823 kB',
                  description: 'Toegankelijke versie van digitaal tellingbestand 510c',
                },
              ]}
            />
          </section>

          <section id="uitleg">
            <ResultsTimeline
              title="Hoe zijn de resultaten tot stand gekomen?"
              description="Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie. Die telresultaten staan in het verslag van het gemeentelijk stembureau/stembureau voor het openbaar lichaam."
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
