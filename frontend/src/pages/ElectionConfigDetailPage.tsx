import { Link, useNavigate, useParams } from 'react-router-dom'
import { Layout } from '../components/Layout.tsx'
import PageTop from '../components/DetailPage/PageTop.tsx'
import SharedTabs from '../components/DetailPage/SharedTabs.tsx'
import SearchBar from '../components/SearchBar.tsx'
import type { SearchListOption } from '../components/SearchBar.tsx'
import { appRoutes } from '../utils/routes.ts'
import { useElectionConfig, useRegions } from '../hooks/queries.ts'


export function ElectionConfigDetailPage() {
  
  const navigate = useNavigate()
  const { electionConfigSlug} = useParams<{ electionConfigSlug: string }>()
  const { data: electionConfig, isLoading, isError, refetch } = useElectionConfig(electionConfigSlug)
  const { data: regions } = useRegions(electionConfigSlug, undefined, 'GEMEENTE')

  const electionLabel = electionConfig?.label ?? 'Verkiezing laden…'

  function navigateToGemeente(option: SearchListOption) {
    navigate(appRoutes.municipalityDetailPollingstationList(electionConfigSlug ?? '', option.id))
  }

  if (isLoading) {
    return (
      <Layout title={electionLabel} description="Telresultaten laden…">
        <p>Verkiezing laden…</p>
      </Layout>
    )
  }

  if (isError || !electionConfig) {
    return (
      <Layout title="Verkiezing niet gevonden" description="Kan verkiezing niet laden.">
        <p>Kan verkiezing niet laden.</p>
        <button type="button" onClick={() => refetch()}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }


  const regionOptions: SearchListOption[] = (regions ?? [])
    .filter((region) => region.region_name)
    .map(({ slug, region_name }) => ({ id: slug, label: region_name }))

  const regionsByLetter = regionOptions.reduce<Record<string, SearchListOption[]>>((grouped, option) => {
    const name = option.label.startsWith("'s-") ? option.label.slice(3) : option.label
    const letter = name[0].toUpperCase()
    ;(grouped[letter] ??= []).push(option)
    return grouped
  }, {})


  return (
    <Layout
      title={`Telresultaten ${electionConfig.label}`}
      description={`Bekijk de telresultaten per gemeente van de ${electionConfig.label}.`}
    >
      <PageTop
        title={`Telresultaten ${electionConfig.label}`}
        subtitle={`Verkiezingsdag: ${electionConfig.date ? new Date(electionConfig.date).toLocaleDateString('nl-NL', { year: 'numeric', month: 'long', day: 'numeric' }) : ''}`}
        breadcrumb={[
          { href: '/', label: 'Home' },
          { href: appRoutes.electionConfigDetailMunicipality(electionConfigSlug ?? ''), label: electionConfig.label},
        ]}
        tabs={<SharedTabs tabs={[
          { label: 'Gemeente', value: appRoutes.electionConfigDetailMunicipality(electionConfig.slug), activePatterns: ['/:electionConfigSlug/gemeente'] },
        ]} />}

      />

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
              <Link key={municipality.id} to={appRoutes.municipalityDetailPollingstationList(electionConfig.slug, municipality.id)}>
                <span>{municipality.label}</span>
                <span className="gemeente-chevron">{'>'}</span>
              </Link>
            ))}
          </div>
        ))}
      </div>
    </Layout>
  )
}
