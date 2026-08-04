import { useNavigate } from 'react-router-dom'

import { Link } from 'react-router-dom'
import SearchBar from '../SearchBar'
import type { SearchListOption } from '../SearchBar'
import type { ElectionConfig } from '../../api/types'
import { appRoutes } from '../../utils/routes'
import { getRegionLabel } from '../../utils/region'
import type { Region, RegionCategory } from '../../api/types'


type Props = {
  electionConfig: ElectionConfig
  regions: Region[] | undefined
  regionCategory: Extract<RegionCategory, 'GEMEENTE' | 'STEMBUREAU' | 'WATERSCHAP'>
  parentRegionSlug?: string
  parentCsbSlug?: string
  regionTitle?: string
}

export function RegionList({
  electionConfig,
  regions,
  regionCategory,
  parentRegionSlug,
  parentCsbSlug,
  regionTitle
}: Props) {


  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? '', option.id, option.csbSlug))
  }

  function navigateToPollingStation(option: SearchListOption) {
    if (!parentRegionSlug) return
    navigate(appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug))
  }

  function navigateToWaterschap(option: SearchListOption) {
    navigate(appRoutes.csbResults(electionConfig.slug ?? '', option.id))
  }

  let navigateToRegion: (option: SearchListOption) => void;
  if (regionCategory === 'STEMBUREAU') {
    navigateToRegion = navigateToPollingStation;
  } else if (regionCategory === 'WATERSCHAP') {
    navigateToRegion = navigateToWaterschap;
  } else {
    navigateToRegion = navigateToGemeente;
  }

  function getRegionRoute(option: SearchListOption) {
    if (regionCategory === 'STEMBUREAU' && parentRegionSlug) {
      return appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id, parentCsbSlug)
    } else if (regionCategory === 'WATERSCHAP') {
      return appRoutes.csbResults(electionConfig.slug, option.id)
    } else {
      return appRoutes.municipalityPollingstationList(electionConfig.slug, option.id, option.csbSlug)
    }
  }

  const visibleRegions = (regions ?? []).filter((region) => region.region_name)

  const nameCounts = visibleRegions.reduce<Record<string, number>>((counts, region) => {
    counts[region.region_name] = (counts[region.region_name] ?? 0) + 1
    return counts
  }, {})

  const isPollingStationList = regionCategory === 'STEMBUREAU'

  const regionOptions: SearchListOption[] = visibleRegions.map((region) => {
    const isAmbiguous = nameCounts[region.region_name] > 1 && Boolean(region.csb_name)
    const label = isAmbiguous ? `${region.region_name} - ${region.csb_name}` : region.region_name
    return {
      id: region.slug,
      label,
      sortName: region.region_name,
      stationNumber: isPollingStationList ? region.station_number ?? undefined : undefined,
      csbSlug: region.csb_slug ?? undefined,
    }
  })

  function compareByStationNumber(a: SearchListOption, b: SearchListOption): number {
    return (a.stationNumber ?? 0) - (b.stationNumber ?? 0)
  }

  const sortedPollingStations = regionOptions.slice().sort(compareByStationNumber)

  const regionsByLetter = regionOptions.reduce<Record<string, SearchListOption[]>>((grouped, option) => {
    const sortName = option.sortName ?? option.label
    // handle 's-Gravenhage and 's-Hertogenbosch
    const name = sortName.startsWith("'s-") ? sortName.slice(3) : sortName
    const letter = name[0].toUpperCase()
      ; (grouped[letter] ??= []).push(option)
    return grouped
  }, {})

  return (
    <div className="page-main">

      {isPollingStationList && (<h2 className="mb-4 text-2xl font-bold font-title">
          {sortedPollingStations.length} stembureaus in {regionTitle}
      </h2>)}

      <SearchBar
        regionCategory={regionCategory}
        options={regionOptions}
        onSelect={navigateToRegion}
      />

      {!isPollingStationList && (<h2 className="mb-4 text-2xl font-bold font-title">
        Vind een {getRegionLabel(regionCategory).toLowerCase()} van A tot Z
      </h2>)}

      {isPollingStationList ? (
        <div className="mb-5 max-w-2xl grid grid-cols-[max-content_auto_max-content]">
          {sortedPollingStations.map((station) => (
            <Link
              key={`${station.id}-${station.csbSlug ?? ''}`}
              to={getRegionRoute(station)}
              className="items-center gap-4 hover:no-underline! odd:bg-blue-50 hover:bg-blue-100 py-4 px-6 grid col-span-3 grid-cols-subgrid"
            >
              <span className="font-light text-gray-700">{station.stationNumber}</span>
              <span className="underline">{station.label}</span>
              <span className="gemeente-chevron">{'>'}</span>
            </Link>
          ))}
        </div>
      ) : (
        Object.entries(regionsByLetter)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([letter, municipalities]) => (
            <div key={letter} className="searchlist-section">
              <div className="searchlist-letter">{letter}</div>
              {municipalities.map((municipality) => (
                <Link
                  key={`${municipality.id}-${municipality.csbSlug ?? ''}`}
                  to={getRegionRoute(municipality)}
                >
                  <span>{municipality.label}</span>
                  <span className="gemeente-chevron">{'>'}</span>
                </Link>
              ))}
            </div>
          ))
      )}
    </div>
  )
}
