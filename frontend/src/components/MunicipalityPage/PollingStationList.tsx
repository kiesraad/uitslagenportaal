import { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { Region } from '../../api/types.ts'
import { InfoBox } from '../InfoBox.tsx'
import SearchBar from '../SearchBar.tsx'
import type { SearchListOption } from '../SearchBar.tsx'
import { appRoutes } from '../../utils/routes.ts'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
// import { faMap } from '@fortawesome/free-regular-svg-icons'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'

import { useRegions } from '../../hooks/queries.ts'


type Props = {
  region: Region
  electionConfigSlug: string
  regionSlug: string
}

export default function PollingStationList({ region, electionConfigSlug, regionSlug }: Props) {
  const navigate = useNavigate()
  const { data: pollingStations } = useRegions(electionConfigSlug, regionSlug, 'STEMBUREAU')

  const pollingStationOptions = useMemo<SearchListOption[]>(
    () =>
      (pollingStations ?? []).map((pollingStation) => ({
        id: pollingStation.slug,
        label: pollingStation.region_name,
        searchText: `${pollingStation.slug} ${pollingStation.region_name}`,
        content: pollingStation.region_name,
      })),
    [pollingStations],
  )

  function navigateToPollingStation(option: SearchListOption) {
    navigate(appRoutes.pollingStationResults(electionConfigSlug, regionSlug, option.id))
  }

  return (
    <div className="page-main">
      <h3 className="stations-count-title">{pollingStations?.length ?? 0} stembureaus in de gemeente {region.region_name}</h3>
      <div className="search-box">
        <SearchBar
          inputId="stembureau-search"
          label="Zoek op naam, adres of stembureau-nummer"
          options={pollingStationOptions}
          placeholder="Bijv. Gymzaal de Boom"
          submitBehavior="first-match"
          onSelect={navigateToPollingStation}
        >
          {/* <button
            className="view-map-btn"
            type="button"
            aria-label="Zie kaart"
          >
            <FontAwesomeIcon icon={faMap} />
            <span>Bekijk kaart</span>
          </button> */}
        </SearchBar>
      </div>

      <div className="searchlist-section">
        {(pollingStations ?? []).map((pollingStation) => (
          <Link
            key={pollingStation.slug}
            to={appRoutes.pollingStationResults(electionConfigSlug, regionSlug, pollingStation.slug)}
          >
            <span>{pollingStation.region_name}</span>
            <span className="gemeente-chevron">{'>'}</span>
          </Link>
        ))}
      </div>

      <InfoBox>
        <h4>Klopt er iets niet?</h4>
        <span>
          Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de
          stemmen. Fouten die na 14 december 10:00 worden gemeld, kunnen we nog
          onderzoeken en herstellen. Dan kan de juiste informatie mee in de
          officiele uitslag.
        </span>
        <p>
          <Link to={appRoutes.reportError(regionSlug)}>Meld een fout of iets dat niet klopt <FontAwesomeIcon icon={faArrowRight} /></Link>
        </p>
      </InfoBox>
    </div>
  )
}
