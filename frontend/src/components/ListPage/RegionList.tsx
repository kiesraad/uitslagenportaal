import { useNavigate } from 'react-router-dom'

import { Link } from 'react-router-dom'
import SearchBar from '../SearchBar'
import type { SearchListOption } from '../SearchBar'
import type { ElectionConfig } from '../../api/types'
import { appRoutes } from '../../utils/routes'
import type { Region, RegionCategory } from '../../api/types'
import { getRegionLabel } from '../../utils/region.ts'


type Props = {
  electionConfig: ElectionConfig
  regions: Region[] | undefined
  regionCategory: RegionCategory
}

export function RegionList({
  electionConfig,
  regions,
  regionCategory,
}: Props) {


  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? '', option.id))
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
        inputId="gemeente-search"
        label={`Zoek ${getRegionLabel(regionCategory).toLowerCase()}`}
        options={regionOptions}
        placeholder="Bijv. Zoetermeer"
        onSelect={navigateToGemeente}
      />

      <h2 className="searchlist-title">Vind een gemeente van A tot Z</h2>

      {Object.entries(regionsByLetter).map(([letter, municipalities]) => (
        <div key={letter} className="searchlist-section">
          <div className="searchlist-letter">{letter}</div>
          {municipalities.map((municipality) => (
            <Link
              key={municipality.id}
              to={appRoutes.municipalityPollingstationList(electionConfig.slug, municipality.id)}
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