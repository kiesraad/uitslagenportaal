import { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import POLLING_STATIONS from '../../assets/stembureaus_lisserdam.json'
import { InfoBox } from '../../components/InfoBox'
import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import SharedTabs from '../../components/GemeentePage/SharedTabs'
import SearchListSearch, { type SearchListOption } from '../../components/SearchListSearch'
import { appRoutes } from '../../utils/routes'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faMap } from '@fortawesome/free-regular-svg-icons'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'

type Props = {
  gemeente: string
}

export default function ResultsAvailable({ gemeente }: Props) {
  const navigate = useNavigate()
  const municipalityRoute = appRoutes.municipality(gemeente)
  const municipalityResultsRoute = appRoutes.municipalityResults(gemeente)
  const pollingStationGroups = useMemo(() => {
    let offset = 0

    return Object.entries(POLLING_STATIONS).map(([district, stations]) => {
      const numberedStations = stations.map((stembureau) => ({
        district,
        stembureau
      }))

      offset += stations.length

      return {
        district,
        stations: numberedStations,
      }
    })
  }, [])
  const pollingStationOptions = useMemo<SearchListOption[]>(
    () =>
      pollingStationGroups.flatMap(({ stations }) =>
        stations.map(({ district, stembureau }) => ({
          id: `${stembureau.id}-${stembureau.name}`,
          label: stembureau.name,
          searchText: `${stembureau.id} stations.name ${district} ${stembureau.name}`,
          content: `${stembureau.id} ${stembureau.name}`,
        })),
      ),
    [pollingStationGroups],
  )

  function navigateToPollingStation(option: SearchListOption) {
    navigate(appRoutes.pollingStationResults(gemeente, option.label))
  }

  return (
    <Layout
      title="Resultaten per stembureau"
      description="Resultaten per stembureau"
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

      <div className="page-main">
        <h3 className="stations-count-title">28 stembureaus in de gemeente {gemeente}</h3>
        <div className="search-box">
          <SearchListSearch
            inputId="stembureau-search"
            label="Zoek op naam, adres of stembureau-nummer"
            options={pollingStationOptions}
            placeholder="Bijv. Gymzaal de Boom"
            submitBehavior="first-match"
            onSelect={navigateToPollingStation}
          >
            <button
              className="view-map-btn"
              type="button"
              aria-label="Zie kaart"
            >
              <FontAwesomeIcon icon={faMap} />
              <span>Bekijk kaart</span>
            </button>
          </SearchListSearch>
        </div>

        {pollingStationGroups.map(({ district, stations }) => (
          <div key={district} className="searchlist-section">
            <div className="searchlist-letter">{district}</div>
            {stations.map(({ stembureau }) => (
              <Link
                key={stembureau.name}
                to={appRoutes.pollingStationResults(gemeente, stembureau.name)}
              >
                <div><span style={{ color: 'var(--c-text)', marginRight: '1rem' }}>{stembureau.id}</span>{stembureau.name}</div>
                <span className="gemeente-chevron">{'>'}</span>
              </Link>
            ))}
          </div>
        ))}

        <InfoBox>
          <h4>Klopt er iets niet?</h4>
          <span>
            Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de
            stemmen. Fouten die na 14 december 10:00 worden gemeld, kunnen we nog
            onderzoeken en herstellen. Dan kan de juiste informatie mee in de
            officiele uitslag.
          </span>
          <p>
            <Link to={appRoutes.reportError(gemeente)}>Meld een fout of iets dat niet klopt <FontAwesomeIcon icon={faArrowRight} /></Link>
          </p>
        </InfoBox>
      </div>
    </Layout>
  )
}
