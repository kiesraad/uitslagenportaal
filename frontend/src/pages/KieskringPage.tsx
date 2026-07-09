import { Layout } from '../components/Layout'
import PageTop from '../components/GemeentePage/PageTop'
import SharedTabs from '../components/GemeentePage/SharedTabs'
import { appRoutes } from '../utils/routes'
import { Link } from 'react-router'
import KIESKRINGEN from '../assets/kieskringen.json'

export function KieskringPage() {
  return (
    <Layout
      title="Kieskring – Telresultaten Tweede Kamerverkiezing 2025"
      description="Telresultaten per kieskring van de Tweede Kamerverkiezing 2025."
    >
      <PageTop
        title="Telresultaten Tweede Kamerverkiezing 2025"
        subtitle="Vond plaats op: 8 december 2025"
        breadcrumb={[
          {
            href: '/',
            label: 'Home',
          },
          {
            href: appRoutes.municipalitySearch(),
            label: 'Tweede Kamerverkiezing 2025',
          },
        ]}
        tabs={<SharedTabs tabs={[
          { label: 'Gemeente', value: appRoutes.municipalitySearch(), activePatterns: ['/gemeente', '/gemeente/*'] },
          { label: 'Kieskring', value: '/kieskring', activePatterns: ['/kieskring', '/kieskring/*'] },
          { label: 'Nederland', value: '/nederland', activePatterns: ['/nederland', '/nederland/*'] },
        ]} />}
      />

      <div className={'page-main page-main-w-half'}>
        <section>
          <h3 className="mb-5">Kieskringen</h3>
          <p>
            Nederland is verdeeld in 20 kieskringen om het tellen en verwerken van stemmen overzichtelijk te organiseren. Benieuwd in welke kieskring uw gemeente valt? Dat staat vermeld op <Link to={'/gemeente'}>de pagina van uw gemeente.</Link>
          </p>
        </section>

        <section className="searchlist-section mt-8">
          {KIESKRINGEN.map((kieskringen) => (
            <Link
              key={kieskringen.kieskring_nr}
              to={appRoutes.kieskring(kieskringen.name)}
            >
              <div><span style={{ color: 'var(--c-text)', marginRight: '1rem' }}>{kieskringen.kieskring_nr}</span>{kieskringen.name}</div>
              <span className="gemeente-chevron">{'>'}</span>
            </Link>
          ))}
        </section>
      </div>
    </Layout>
  )
}
