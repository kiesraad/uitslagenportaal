import { Link } from 'react-router-dom'
import { Layout } from '../components/Layout.tsx'
import PageTop from '../components/PageTop.tsx'
import { appRoutes } from '../utils/routes.ts'

export function NotFoundPage() {
  return (
    <Layout title="Pagina niet gevonden">
      <div className="not-found-top">
        <PageTop title="Pagina niet gevonden" />
      </div>
      <div className="page-main">
        <div className="page-space-2 max-w-2xl">
          <p className="text-lg">
            De pagina die u wilde zien of het bestand dat u wilde bekijken is niet gevonden.
          </p>

          <section className="flex flex-col gap-3">
            <h2>U kunt de informatie die u zoekt mogelijk vinden via de volgende pagina's:</h2>
            <ul className="flex flex-col gap-2 list-none p-0 m-0">
              <li className="flex items-center gap-2">
                <span className="not-found-chevron">›</span>
                <Link to={appRoutes.home()}>Homepage</Link>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </Layout>
  )
}
