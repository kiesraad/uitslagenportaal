import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import SharedTabs from '../../components/GemeentePage/SharedTabs'
import { appRoutes } from '../../utils/routes'
import { Link, useParams } from 'react-router'
import KIESKRINGEN from '../../assets/kieskringen.json'
import GEMEENTEN from '../../assets/gemeenten.json'

export default function KieskringPerGemeente() {
    const { kieskring: kieskringParam } = useParams<{ kieskring: string }>()
    const kieskring = decodeURIComponent(kieskringParam ?? '')

    const kieskringNr = KIESKRINGEN.find(kring => kring.name === kieskring)?.kieskring_nr;

    return (
        <Layout
            title="Resultaten per stembureau"
            description="Resultaten per stembureau"
        >
            <PageTop
                title={`Kieskring ${kieskringNr} - ${kieskring}`}
                subtitle="Geplaatst op: 10 december 2025 - 12:17"
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
                ]}
                tabs={<SharedTabs tabs={[
                    { label: 'Hele kieskring', value: appRoutes.kieskring(kieskring), activePatterns: ['/kieskring', '/kieskring/'] },
                    { label: 'Per gemeente', value: appRoutes.kieskringGemeente(kieskring), activePatterns: ['/kieskring/*'] }
                ]} />}
            />

            <div className="page-main page-main-w-half">
                <h2 className="result-unpublished">
                    Alle gemeenten in kieskring {kieskringNr}
                </h2>

                {Object.entries(GEMEENTEN).map(([letter, gemeenten]) => (
                    <div key={letter} className="searchlist-section">
                        <div className="searchlist-letter">{letter}</div>
                        {gemeenten.map((gemeente) => (
                            <Link key={gemeente} to={appRoutes.municipality(gemeente)}>
                                <span>{gemeente}</span>
                                <span className="gemeente-chevron">›</span>
                            </Link>
                        ))}
                    </div>
                ))}
            </div>
        </Layout>
    )
}
