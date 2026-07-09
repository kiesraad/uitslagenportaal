import { Layout } from '../../components/Layout'
import { InfoBox } from '../../components/InfoBox'
import PageTop from '../../components/GemeentePage/PageTop'
import type { Step } from '../../components/Timeline'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import { appRoutes } from '../../utils/routes'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import KIESKRINGEN from '../../assets/kieskringen.json'
import SharedTabs from '../../components/GemeentePage/SharedTabs'

const STEPS: Step[] = [
  {
    state: 'pending',
    title: 'De Kiesraad publiceert de uitslag',
    date: 'Verwacht: 15 december 11:00',
    body: 'In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen.',
  },
  {
    state: 'pending',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: `De Kiesraad controleert de telresultaten van alle kieskringen, gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er [meldingen van kiezers](#) die onderzocht moeten worden? Als het nodig is, worden de resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen.  
    
Pas als alles klopt worden de resultaten van alle kieskringen bij elkaar opgeteld tot de landelijke uitslag.
    `,
  },
  {
    state: 'in-progress',
    title: 'Optelling per kieskring',
    date: '9 december op het hoofdstembureau van elke kieskring',
    body: 'De 20 kieskringen in Nederland tellen de resultaten van alle gemeenten in de kieskring bij elkaar op.',
  },
  {
    state: 'done',
    title: 'Gemeenten publiceren telresultaten',
    date: '9 december',
    body: 'De gemeente moet de telresultaten en de processen-verbaal van alle stembureaus zo snel mogelijk na de zitting van het gemeentelijk stembureau publiceren. Dat staat in de Kieswet.',
  },
  {
    state: 'done',
    title: 'Optelling per gemeente',
    date: '9 december op centrale tellocatie in elke gemeente',
    body: 'De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag.',
  },
  {
    state: 'done',
    title: 'Telling in de stembureaus',
    date: '8 december na 21:00 in lokale stembureaus',
    body: 'Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus en wordt gepubliceerd door media en persbureaus. **Het is dus nog niet de officiële uitslag van de Kiesraad.**',
  },
]

type Props = {
  kieskring: string;
}
export default function ResultsNotPublished({ kieskring }: Props) {
  const kieskringNr = KIESKRINGEN.find(kring => kring.name === kieskring)?.kieskring_nr;
  return (
    <Layout
      title={`Kieskring ${kieskring} - resultaten nog niet gepubliceerd`}
      description={`Kieskring ${kieskring} - resultaten nog niet gepubliceerd`}
    >
      <PageTop
        title={`Kieskring ${kieskringNr} - ${kieskring}`}
        subtitle={'Laatste update 9 december 2025 - 9:45'}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
          { href: appRoutes.kieskring(''), label: `Kieskring` },
          { href: appRoutes.kieskring(kieskring), label: `${kieskringNr}: ${kieskring}` },
        ]}
        tabs={<SharedTabs tabs={[
          { label: 'Hele kieskring', value: appRoutes.kieskring(kieskring), activePatterns: ['/kieskring', '/kieskring/*'] },
          { label: 'Per gemeente', value: appRoutes.kieskringGemeente(kieskring), activePatterns: ['/kieskring/*/gemeente'] }
        ]} />}
      />

      <div className={'page-main page-main-w-half'}>
        {/* Not published notice */}
        <h2 className="result-unpublished">
          De telresultaten van Kieskring {kieskringNr} zijn nog niet gepubliceerd
        </h2>

        {/* Info box */}
        <InfoBox>
          <span>
            De telresultaten en processen-verbaal van de gemeente {kieskring} zijn hier
            te zien zodra de gemeente ze publiceert.
          </span>
        </InfoBox>

        {/* How section */}
        <ResultsTimeline
          title="Hoe komen de resultaten tot stand?"
          steps={STEPS}
        />

        {/* FAQ */}
        <InfoBox>
          <h4>Klopt er iets niet?</h4>
          <span>
            Soms gaat er iets mis bij het tellen, opschrijven of het overtypen van de stemmen. Fouten die vóór 14 december 10:00 worden gemeld,
            kunnen we nog onderzoeken en herstellen. Dan telt de juiste informatie mee in de officiële uitslag.
          </span>
          <p>
            <a href="#">Meld een fout of iets dat niet klopt <FontAwesomeIcon icon={faArrowRight} /></a>
          </p>
        </InfoBox>
      </div>
    </Layout>
  )
}
