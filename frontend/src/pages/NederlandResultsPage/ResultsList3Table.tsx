import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import { appRoutes } from '../../utils/routes'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import PageIndex from '../GemeenteSearchResultPage/PageIndex'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import type { Step } from '../../components/Timeline'
import { faFile, faFolder } from '@fortawesome/free-regular-svg-icons'
import { faTable } from '@fortawesome/free-solid-svg-icons'
import ResultsTable from '../../components/ResultsTable'

const STEPS: Step[] = [
    {
        state: 'done',
        title: 'Centraal Stembureau controleert',
        date: 'Tot 14 december 10:00',
        body: `De Kiesraad controleert de telresultaten van alle gemeenten en stembureaus. Zijn alle documenten compleet? Zijn alle stemmen meegeteld? Zijn er meldingen van kiezers die onderzocht moeten worden? Als alles klopt worden de resultaten van alle gemeenten bij elkaar opgeteld, en wordt de uitslag vastgesteld.`,
        files: [
            {
                name: 'Proces-verbaal Model P 22-1',
                url: '#',
                type: 'PDF',
                size: '12 MB',
                description: 'Scan van de telresultaten en zetelverdeling van Nederland',
            },
            {
                name: 'Digitaal telbestand centraal stembureau',
                url: '#',
                type: 'XML',
                size: '56 kB',
                description: 'EML_NL totaaltellingsbestand 510d',
            },
            {
                name: 'Digitale resultaten centraal stembureau',
                url: '#',
                type: 'XML',
                size: '56 kB',
                description: 'EML_NL resultaatbestand 520',
            }
        ]
    },
    {
        state: 'done',
        title: 'Optelling Kieskringen',
        date: '10 december op hoofdstembureau van de kieskring in Arnhem',
        body: `De resultaten van alle gemeenten in Kieskring 7 worden op het hoofdstembureau gecontroleerd bij elkaar opgeteld.

Bekijk de [resultaten per kieskring](#) → `
    },
    {
        state: 'done',
        title: 'Optelling per gemeente',
        date: '9 december op centrale tellocatie in elke gemeente',
        body: `De resultaten van alle stembureaus worden gecontroleerd en van papier overgetypt in de uitslagensoftware en opgeteld. Het gemeentelijk stembureau maakt een verslag en deelt de telresultaten zodat ze kunnen worden meegenomen in de landelijke uitslag.

Bekijk de [resultaten per gemeente](#) → `,
    },
    {
        state: 'done',
        title: 'Telling in de stembureaus',
        date: '8 december na 21:00 in lokale stembureaus',
        body: 'Na het sluiten van de stembussen tellen de leden van het stembureau hoeveel mensen hebben gestemd en hoeveel stemmen elke partij heeft gekregen. De voorlopige uitslag die je in het nieuws ziet is gebaseerd op de eerste tellingen van de stembureaus en wordt gepubliceerd door media en persbureaus. **Het is dus nog niet de officiële uitslag van de Kiesraad.**',
    },
]

export default function ResultsList3Table() {
    const reportHref = appRoutes.reportError('nederland')

    return (
        <Layout
            title="Nederland – Telresultaten Tweede Kamerverkiezing 2025"
            description="Landelijke telresultaten van de Tweede Kamerverkiezing 2025."
        >
            <PageTop
                title={`Telresultaten heel Nederland 
                    Lijst 3 - Eeuwenoude Aarde Unie`}
                subtitle="Gepubliceerd op: 10 december 2025"
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
                ]}
            />

            <div className="page-main">
                <div className="page-space-3">
                    <section className={'page-main-w-half'}>
                        <PageIndex
                            links={[
                                { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
                                { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van de gemeente</>, url: '#processen-verbaal' },
                                { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
                                { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
                            ]}
                        />
                    </section>

                    <section id="telresultaten">
                        <div className={'page-main-w-half mb-6'}>
                            <p style={{fontSize: '1.17em'}}>Telresultaten lijst 3</p>
                            <h3 className="mb-3">Eeuwenoude Aarde Unie</h3>
                            <p>Het centraal stembureau heeft de telresultaten van alle gemeenten en kieskringen gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het proces-verbaal van het centraal stembureau.</p>
                        </div>
                        <ResultsTable />
                    </section>

                    <section id="processen-verbaal" className={'page-main-w-half'}>
                        <ReportsWithResults
                            title="Processen-verbaal met resultaten"
                            description="Onderstaande documenten bevatten de telresultaten en de uitslag van het centraal stembureau (de Kiesraad). De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
                            files={[
                                {
                                    name: `Proces-verbaal Model P 22-1`,
                                    icon: (
                                        <FontAwesomeIcon icon={faFile} />
                                    ),
                                    url: '#',
                                    type: 'PDF',
                                    size: '12 MB',
                                    description: `Scan van de telresultaten en zetelverdeling van Nederland`,
                                },
                                {
                                    name: 'EML_NL totaaltellingsbestand 510d',
                                    type: 'XML',
                                    icon: (
                                        <FontAwesomeIcon icon={faFolder} />
                                    ),
                                    url: '#',
                                    size: '156 kB',
                                    description: 'Output van de optelsoftware, bevat de telresultaten van heel Nederland. Bron van de informatie op deze website. Bron van de informatie op deze pagina.',
                                },
                                {
                                    name: 'EML_NL resultaatbestand 520',
                                    type: 'XLSX',
                                    icon: (
                                        <FontAwesomeIcon icon={faTable} />
                                    ),
                                    url: '#',
                                    size: '102 kB',
                                    description: 'Output van de optelsoftware, bevat de zetelverdeling',
                                },
                            ]}
                        />
                    </section>

                    <section id="uitleg" className={'page-main-w-half'}>
                        <ResultsTimeline
                            title="Hoe zijn de resultaten tot stand gekomen?"
                            description="Het centraal stembureau (de Kiesraad) controleert de telresultaten van alle gemeenten en stembureaus. Als alles klopt worden de resultaten van alle gemeenten bij elkaar opgeteld, en wordt de uitslag vastgesteld."
                            steps={STEPS}
                        />
                    </section>

                    <section className={'page-main-w-half'}>
                        <IssueNotice id="fout-melden" reportHref={reportHref} />
                    </section>
                </div>
            </div>
        </Layout>
    )
}
