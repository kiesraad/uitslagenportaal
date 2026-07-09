import { Link, useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import PageTop from '../components/GemeentePage/PageTop'
import GEMEENTEN from '../assets/gemeenten.json'
import SharedTabs from '../components/GemeentePage/SharedTabs'
import SearchListSearch, { type SearchListOption } from '../components/SearchListSearch'
import { appRoutes } from '../utils/routes'

const ALL_GEMEENTEN: string[] = Object.values(GEMEENTEN).flat()
const GEMEENTE_OPTIONS: SearchListOption[] = ALL_GEMEENTEN.map((gemeente) => ({
  id: gemeente,
  label: gemeente,
}))

export function GemeentePage() {
  const navigate = useNavigate()

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipality(option.label))
  }

  return (
    <Layout
      title="Telresultaten Tweede Kamerverkiezing 2025"
      description="Bekijk de telresultaten per gemeente van de Tweede Kamerverkiezing 2025."
    >
      <PageTop
        title="Telresultaten Tweede Kamerverkiezing 2025"
        subtitle="Vond plaats op: 8 december 2025"
        breadcrumb={[
          { href: '/', label: 'Home' },
          { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
        ]}
        tabs={<SharedTabs tabs={[
          { label: 'Gemeente', value: appRoutes.municipalitySearch(), activePatterns: ['/gemeente', '/gemeente/*'] },
          { label: 'Kieskring', value: '/kieskring', activePatterns: ['/kieskring', '/kieskring/*'] },
          { label: 'Nederland', value: '/nederland', activePatterns: ['/nederland', '/nederland/*'] },
        ]} />}
      />

      <div className="page-main">
        <SearchListSearch
          inputId="gemeente-search"
          label="Zoek plaats of gemeente"
          options={GEMEENTE_OPTIONS}
          placeholder="Bijv. Zoetermeer"
          onSelect={navigateToGemeente}
        />

        <h2 className="searchlist-title">Vind een gemeente van A tot Z</h2>

        {Object.entries(GEMEENTEN).map(([letter, gemeenten]) => (
          <div key={letter} className="searchlist-section">
            <div className="searchlist-letter">{letter}</div>
            {gemeenten.map((gemeente) => (
              <Link key={gemeente} to={appRoutes.municipality(gemeente)}>
                <span>{gemeente}</span>
                <span className="gemeente-chevron">{'>'}</span>
              </Link>
            ))}
          </div>
        ))}
      </div>
    </Layout>
  )
}
