import { useNavigate } from 'react-router-dom'

import { Link } from 'react-router-dom'
import SearchBar from '../SearchBar'
import type { SearchListOption } from '../SearchBar'
import type { ElectionConfig } from '../../api/types'
import { appRoutes } from '../../utils/routes'

type Props = {
  electionConfig: ElectionConfig
  electionConfigSlug: string
  regionOptions: SearchListOption[]
  regionsByLetter: Record<string, SearchListOption[]>
}

export function RegionList({
  electionConfig,
  regionOptions,
  regionsByLetter,
}: Props) {

  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityPollingstationList(electionConfig.slug ?? '', option.id))
  }

  return (
    <div className="page-main">
      <SearchBar
        inputId="gemeente-search"
        label="Zoek plaats of gemeente"
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