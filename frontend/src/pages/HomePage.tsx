import { Link } from 'react-router'
import { Layout } from '../components/Layout.tsx'
import Timeline, { type TimelineEntry } from '../components/Timeline.tsx'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHourglass } from '@fortawesome/free-regular-svg-icons'
import { faArrowUpRightFromSquare } from '@fortawesome/free-solid-svg-icons'
import { HeroGrid } from '../components/HomePage/HeroGrid.tsx'
import { useElectionConfigs } from '../hooks/queries.ts'
import { appRoutes } from '../utils/routes.ts'
import type { ElectionConfig } from '../api/types.ts'

export function HomePage() {
  const { data, isLoading, isError, refetch } = useElectionConfigs()
  const election_configs: ElectionConfig[] = data ?? []
  const hasResult = election_configs.length > 0

  // If there is only one election and it has timeline entries, build the timeline
  let timelineEntries: TimelineEntry[] = []
  if (election_configs.length === 1 && election_configs[0]?.timeline_entries?.length) {
    timelineEntries = election_configs[0].timeline_entries
      .slice()
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      .map((entry) => ({
        status: entry.status,
        title: entry.title,
        date: entry.date,
        body: entry.body,
      }))
  }


  return (
    <Layout
      title="Home"
      description="De telresultaten van alle stembureaus in Nederland."
    >
      <section className={'page-top home-page-hero'}>
        <div className={'home-page-hero-left'}>
          <h1 className="text-3xl sm:text-4xl font-title font-bold">De telresultaten van alle <br /> stembureaus in Nederland.</h1>
          <p>Op deze website publiceert de Kiesraad de telresultaten van alle gemeenten en stembureaus. Je vindt hier ook de brondocumenten waarin stembureaus hun tellingen hebben opgeschreven. Zo kan iedereen controleren of de stemmen goed zijn geteld en in de definitieve uitslag terecht zijn gekomen.</p>

          {isLoading ? (
            <div className={'home-hero-card'}>
              <h2>Bekijk de telresultaten</h2>
              <p>Verkiezingen laden…</p>
            </div>
          ) : isError ? (
            <div className={'home-hero-card'}>
              <h2>Bekijk de telresultaten</h2>
              <p>Kan verkiezingen niet laden.</p>
              <button type="button" onClick={() => refetch()}>
                Opnieuw proberen
              </button>
            </div>
          ) : hasResult ? (
            <div className={'home-hero-card'}>
              <h2>Bekijk de telresultaten</h2>
              {election_configs.map((election_config) => (
                <div key={election_config.slug} className={'home-hero-card-link'}>
                  <span className="gemeente-chevron mb-1">›</span>
                  <Link to={appRoutes.electionConfigMunicipalityList(election_config.slug)} className="font-semibold">
                    {election_config.label}
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <div className={'home-hero-card'}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <FontAwesomeIcon icon={faHourglass} />
                <h2>Telresultaten volgen binnenkort</h2>
              </div>
              {/* <p>Op dit moment is de Tweede Kamerverkiezing bezig; u kunt nog stemmen tot  <strong>21.00 uur op 26 november 2025</strong>. In de loop van 27 november verwachten we de eerste telresultaten van het aantal stemmen. Na 3 maanden worden de resultaten weer verwijderd.</p> */}
            </div>
          )}
        </div>

        <HeroGrid />
      </section>

      {election_configs.length === 1 && (
        <>
          <section className="page-main page-main-w-half">
            <h2 className="home-process-title">Hoe komt de uitslag tot stand?</h2>
            <p className="home-process-intro">
              Hieronder wordt stap voor stap uitgelegd hoe het resultaat van de verkiezing tot stand
              komt. Het begint bij het stembureau en eindigt bij de definitieve uitslag die de Kiesraad
              publiceert. Bij iedere stap is er controle, zodat de uitslag klopt.
            </p>

            <Timeline entries={timelineEntries} />
          </section>

          <section className="home-bottom-info page-main-w-half">
            <div className="home-info-box">
              <div className="home-info-body">
                <h3>Benieuwd naar de resultaten in het stembureau waar u gestemd heeft?</h3>
                  {election_configs.map((election_config) => (
                    <div key={election_config.slug} className={'home-hero-card-link'}>
                      <span className="gemeente-chevron">›</span>
                      <Link to={appRoutes.electionConfigMunicipalityList(election_config.slug)}>Bekijk de tellingen per stembureau voor {election_config.label}</Link>
                    </div>
                  ))}
              </div>
            </div>

            <div className="home-external-links">
              <p>
                Deze website is actief vanaf 1 dag vóór de verkiezingen tot drie maanden erna. Wilt u
                uitslagen van eerdere verkiezingen bekijken? <br />
                <span style={{ display: 'flex', alignItems: "center", gap: '0.25rem' }}>
                  Ga dan naar{' '}
                  <a style={{ display: 'flex', alignItems: "center", gap: '0.25rem' }} href="https://www.verkiezingsuitslagen.nl/" target="_blank" rel="noopener noreferrer">
                    Databank verkiezinguitslag
                    <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                  </a>
                </span>
              </p>
            </div>
          </section>
        </>
      )}

    </Layout>
  )
}
