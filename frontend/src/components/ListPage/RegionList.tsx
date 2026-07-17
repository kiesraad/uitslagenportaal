import { useNavigate } from 'react-router-dom'

import { Link } from 'react-router-dom'
import SearchBar from '../SearchBar'
import type { SearchListOption } from '../SearchBar'
import type { ElectionConfig } from '../../api/types'
import { appRoutes } from '../../utils/routes'
import type { Region, RegionCategory } from '../../api/types'


type Props = {
  electionConfig: ElectionConfig
  regions: Region[] | undefined
  regionCategory: Extract<RegionCategory, 'GEMEENTE' | 'STEMBUREAU' | 'WATERSCHAP'>
  parentRegionSlug?: string
}

export function RegionList({
  electionConfig,
  regions,
  regionCategory,
  parentRegionSlug,
}: Props) {


  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? '', option.id))
  }
  
  function navigateToPollingStation(option: SearchListOption) {
    if (!parentRegionSlug) return
    navigate(appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id))
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
      return appRoutes.pollingStationResults(electionConfig.slug, parentRegionSlug, option.id)
    } else if (regionCategory === 'WATERSCHAP') {
      return appRoutes.csbResults(electionConfig.slug, option.id)
    } else {
      return appRoutes.municipalityPollingstationList(electionConfig.slug, option.id)
    }
  }

  const regionOptions: SearchListOption[] = (regions ?? [])
    .filter((region) => region.region_name)
    .map(({ slug, region_name }) => ({ id: slug, label: region_name }))

  const regionsByLetter = regionOptions.reduce<Record<string, SearchListOption[]>>((grouped, option) => {
    const name = option.label.startsWith("'s-") ? option.label.slice(3) : option.label
    const letter = name[0].toUpperCase()
      ; (grouped[letter] ??= []).push(option)
    return grouped
  }, {})

  return (
    <div className="page-main">
      <SearchBar
        regionCategory={regionCategory}
        options={regionOptions}
        onSelect={navigateToRegion}
      />

      <h2 className="searchlist-title">Vind een gemeente van A tot Z</h2>

      {Object.entries(regionsByLetter).map(([letter, municipalities]) => (
        <div key={letter} className="searchlist-section">
          <div className="searchlist-letter">{letter}</div>
          {municipalities.map((municipality) => (
            <Link
              key={municipality.id}
              to={getRegionRoute(municipality)}
            >
              <span>{municipality.label}</span>
              <span className="gemeente-chevron">{'>'}</span>
            </Link>
          ))}
        </div>
      ))}
    </div>
  )
}