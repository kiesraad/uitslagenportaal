import { Layout } from '../../components/Layout'
import { InfoBox } from '../../components/InfoBox'
import PageTop from '../../components/GemeentePage/PageTop'
import Timeline, { type Step } from '../../components/Timeline'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import { appRoutes } from '../../utils/routes'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

const STEPS: Step[] = [
  {
    state: 'pending',
    title: 'De Kiesraad publiceert de uitslag',
    date: 'Verwacht: 15 december 10:00',
    body: 'In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen.',
  },
  {
    state: 'pending',
    title: 'Centraal Stembureau controleert',
    date: 'Tot 14 december 10:00',
    body: 'De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzoek noodzakelijk maken? Als het nodig is, worden de resultaten van bepaalde stembureaus opnieuw geteld om fouten te herstellen. Pas als alles klopt worden de resultaten van alle gemeenten bij elkaar opgeteld tot de landelijke uitslag.',
  },
  {
    state: 'pending',
    title: 'Optelling Kieskring 23',
    date: '10 december op hoofdstembureau in de kieskring in Zwijndrecht',
    body: 'De resultaten van alle gemeenten in Kieskring 23 worden op het hoofdstembureau gecontroleerd en bij elkaar opgeteld.',
    link: 'Bekijk de resultaten van de kieskring 23 →',
  },
  {
    state: 'pending',
    title: 'Gemeente publiceert telresultaten',
    date: 'Binnenkort verwacht',
    body: 'De gemeente moet de telresultaten en de processen-verbaal van alle stembureaus zo snel mogelijk in de zitting van het gemeentelijk stembureau publiceren. Dat staat in de Kieswet.',
  },
  {
    state: 'in-progress',
    title: 'Gemeentelijke optelling',
    date: '9 december op centrale tellocatie in gemeente Lisserdam',
    body: 'Nadat alle stembureaus zijn gesloten en gecorrigeerd worden de resultaten van papieren stemmen zo snel mogelijk na de sluiting geteld. Hiermee maakt het gemeentelijk stembureau een verslag waarna de optelling van de gehele gemeente wordt afgerond.',
  },
  {
    state: 'done',
    title: 'Tellen van de stemmen in het stembureau',
    date: '8 december 21:00 in lokale stembureaus',
    body: 'Na het sluiten van het stembureau tellen de leden van het stembureau hoeveel stemmen er zijn uitgebracht en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus. Dit is niet de officiële uitslag.',
  },
]

type Props = {
    gemeente: string;
}
export default function ResultsNotPublished({ gemeente }: Props) {
  return (
    <Layout
          title={`Gemeente ${gemeente}`}
          description={`Telresultaten Tweede Kamerverkiezing 2025 voor gemeente ${gemeente}.`}
        >
          <PageTop
            title={`Gemeente ${gemeente}`}
            breadcrumb={[
              { href: appRoutes.home(), label: 'Home' },
              { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
              { href: appRoutes.municipality(gemeente), label: `Gemeente ${gemeente}` },
            ]}
          />
    
          <div className={'page-main page-main-w-half'}>
            {/* Not published notice */}
            <p className="result-unpublished">
              De telresultaten van {gemeente} zijn nog niet gepubliceerd
            </p>
    
            {/* Info box */}
            <InfoBox>
              <span>
                De telresultaten en processen-verbaal van de gemeente {gemeente} zijn hier
                te zien zodra de gemeente ze publiceert.
              </span>
            </InfoBox>
    
            {/* How section */}
            <ResultsTimeline 
              title="Hoe komen de resultaten tot stand?"
              steps={STEPS}
            />
    
            {/* Timeline */}
            <Timeline
              steps={STEPS}
            />
    
            {/* FAQ */}
            <InfoBox>
              <h4>Klopt er iets niet?</h4>
              <span>
                Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de
                stemmen. Fouten die na 14 december 10:00 worden gemeld, kunnen we nog
                onderzoeken en herstellen. Dan kan de juiste informatie mee in de
                officiële uitslag.
              </span>
              <p>
                <a href="#">Meld een fout of iets dat niet klopt <FontAwesomeIcon icon={faArrowRight} /></a>
              </p>
            </InfoBox>
          </div>
        </Layout>
  )
}
