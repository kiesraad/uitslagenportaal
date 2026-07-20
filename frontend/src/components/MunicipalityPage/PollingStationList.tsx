import { useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { Region } from '../../api/types.ts'
import SearchBar from '../SearchBar.tsx'
import type { SearchListOption } from '../SearchBar.tsx'

import { appRoutes } from '../../utils/routes.ts'
import { useRegions } from '../../hooks/queries.ts'
import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'


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

      <IssueNotice />

    </div>
  )
}
