import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import { appRoutes } from '../../utils/routes'
import VotesList from '../../components/GemeentePage/VotesList'
import VOTES_CAST_CANDIDATE from '../../assets/votes_cast_candidate.json'
import VOTES_CAST_LIST3 from '../../assets/votes_cast_lijst3.json'
import { useParams } from 'react-router-dom'

const LIST_NUMBER = 3
const LIST_SLUG = 'eeuwenoude-aarde-unie'

export default function ResultsForCandidate() {
    const { candidate: candidateParam } = useParams()
    const candidateName = decodeURIComponent(candidateParam || '')
    const listRoute = appRoutes.nederlandList(LIST_NUMBER, LIST_SLUG)
    const candidateRoute = appRoutes.nederlandCandidate(LIST_NUMBER, LIST_SLUG, candidateName)

    const findCandidate = VOTES_CAST_LIST3.find((candidate) => candidate.url === candidateRoute)
    const candidatePosition = findCandidate ? VOTES_CAST_LIST3.indexOf(findCandidate) + 1 : undefined

    return (
        <Layout
            title={`Nederland - Telresultaten heel Nederland - Lijst 3, ${findCandidate?.name ?? 'Onbekende kandidaat'}`}
            description="Landelijke telresultaten van de Tweede Kamerverkiezing 2025."
        >
            <PageTop
                title={`Telresultaten heel Nederland - Lijst 3, 
                    ${findCandidate?.name ?? 'Onbekende kandidaat'}`}
                subtitle="Geplaatst op: 10 december 2025"
                breadcrumb={[
                    {
                        href: '/',
                        label: 'Home',
                    },
                    {
                        href: appRoutes.municipalitySearch(),
                        label: 'Tweede Kamerverkiezing 2025',
                    },
                    {
                        href: appRoutes.nederland(),
                        label: 'Heel Nederland',
                    },
                    {
                        href: listRoute,
                        label: 'Lijst 3 - Eeuwenoude Aarde Unie',
                    },
                ]}
            />

            <div className="page-main page-main-w-half">
                <div className="page-space-3">
                    <section>
                        <p style={{ fontSize: '1.17em' }}>Telresultaten per kieskring</p>
                        <h3 className="mb-3">{findCandidate?.name || 'Onbekende kandidaat'}</h3>

                        <VotesList
                            votes={VOTES_CAST_CANDIDATE}
                            total={{ label: candidatePosition ? `Totaal stemmen kandidaat ${candidatePosition}` : 'Totaal stemmen kandidaat', value: 385382 }}
                            columns={['Kieskring', 'Aantal stemmen']}
                        />
                    </section>
                </div>
            </div>
        </Layout>
    )
}
