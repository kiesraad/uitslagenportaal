import { Link } from 'react-router-dom'
import { Layout } from '../components/Layout'
import Timeline, { type Step } from '../components/Timeline'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHourglass } from '@fortawesome/free-regular-svg-icons'
import { faArrowUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { HeroGrid } from '../components/HeroGrid'

const STEPS: Step[] = [
  {
    state: 'pending',
    title: 'De Kiesraad publiceert de uitslag',
    date: 'Verwacht: 15 december 11:00',
    body: 'In de uitslag staat hoeveel stemmen elke kandidaat heeft gekregen, hoeveel zetels elke partij krijgt en welke mensen in de Tweede Kamer komen.',
  },
  {
    state: 'in-progress',
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

export function HomePage() {
  var hasResult = true
  return (
    <Layout
      title="Home"
      description="De telresultaten van alle stembureaus in Nederland."
    >
      <section className={'page-top home-page-hero'}>
        <div className={'home-page-hero-left'}>
          <h1 className="page-title">De telresultaten van alle <br /> stembureaus in Nederland.</h1>
          <p className="page-subtitle">Op deze website publiceert de Kiesraad de telresultaten van alle gemeenten en stembureaus. Je vindt hier ook de brondocumenten waarin stembureaus hun tellingen hebben opgeschreven. Zo kan iedereen controleren of de stemmen goed zijn geteld en in de definitieve uitslag terecht zijn gekomen.</p>

          {hasResult ? (
            <div className={'home-hero-card'}>
              <h2>Bekijk de telresultaten</h2>
              <div className={'home-hero-card-link'}>
                <span className="gemeente-chevron">›</span>
                <a href="/gemeente">Tweede Kamerverkiezing 2025</a>
              </div>
            </div>
          ) : (
            <div className={'home-hero-card'}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FontAwesomeIcon icon={faHourglass} />
                <h2>Telresultaten volgen binnenkort</h2>
              </div>
              <p>Op dit moment is de Tweede Kamerverkiezing bezig; u kunt nog stemmen tot  <strong>21.00 uur op 26 november 2025</strong>. In de loop van 27 november verwachten we de eerste telresultaten van het aantal stemmen. Na 3 maanden worden de resultaten weer verwijderd.</p>
            </div>
          )}
        </div>

        <HeroGrid/>
      </section>

      <section className="page-main page-main-w-half">
        <h2 className="home-process-title">Hoe komt de uitslag tot stand?</h2>
        <p className="home-process-intro">
          Hieronder wordt stap voor stap uitgelegd hoe het resultaat van de verkiezing tot stand
          komt. Het begint bij het stembureau en eindigt bij de definitieve uitslag die de Kiesraad
          publiceert. Bij iedere stap is er controle, zodat de uitslag klopt.
        </p>

        <Timeline steps={STEPS} />
      </section>

      <section className="home-bottom-info page-main-w-half">
        <div className="home-info-box">
          <div className="home-info-body">
            <h3>Benieuwd naar de resultaten in het stembureau waar u gestemd heeft?</h3>
            <p>
              <span className="gemeente-chevron">›</span>
              <Link to="/gemeente">Bekijk de tellingen per stembureau</Link>
            </p>
          </div>
        </div>

        <div className="home-external-links">
          <p>

            Deze website is actief vanaf 1 dag vóór de verkiezingen tot drie maanden erna. Wilt u
            uitslagen van eerdere verkiezingen bekijken? <br />
            <span style={{ display: 'flex', alignItems: "center", gap: '0.25rem' }}>
              Ga dan naar {' '}
              <a style={{ display: 'flex', alignItems: "center", gap: '0.25rem' }} href="https://www.verkiezingsuitslagen.nl/" target="_blank" rel="noopener noreferrer">
                Databank verkiezinguitslag
                <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
              </a>
            </span>
          </p>
        </div>
      </section>
    </Layout>
  )
}
