import { Layout } from '../../components/Layout'
import PageTop from '../../components/GemeentePage/PageTop'
import SharedTabs from '../../components/GemeentePage/SharedTabs'
import { appRoutes } from '../../utils/routes'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import PageIndex from '../GemeenteSearchResultPage/PageIndex'
import VotesResume from '../../components/GemeentePage/VotesResume'
import VotesList from '../../components/GemeentePage/VotesList'
import ReportsWithResults from '../../components/GemeentePage/ReportsWithResults'
import ResultsTimeline from '../../components/GemeentePage/ResultsTimeline'
import IssueNotice from '../../components/GemeentePage/IssueNotice'
import ResultsSourceBox from '../../components/GemeentePage/ResultsSourceBox'
import type { Step } from '../../components/Timeline'
import { faFile, faFolder } from '@fortawesome/free-regular-svg-icons'
import { faTable } from '@fortawesome/free-solid-svg-icons'
import VOTES_CAST_NEDERLAND from '../../assets/votes_cast_nederland.json'

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
                name: 'Digitaal totaaltelling centraal stembureau',
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

export default function ResultsVotesCast() {
    const reportHref = appRoutes.reportError('nederland')

    return (
        <Layout
            title="Nederland – Telresultaten Tweede Kamerverkiezing 2025"
            description="Landelijke telresultaten van de Tweede Kamerverkiezing 2025."
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

            <div className="page-main page-main-two-columns">
                <div className="page-space-3">
                    <PageIndex
                        links={[
                            { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
                            { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van de gemeente</>, url: '#processen-verbaal' },
                            { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
                            { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
                        ]}
                    />

                    <section id="telresultaten">
                        <h3 className="mb-2">Telresultaten</h3>
                        <p>Het hoofdstembureau heeft de telresultaten van alle gemeentes in kieskring gecontroleerd, overgenomen en bij elkaar opgeteld. Hieronder ziet u de telresultaten zoals ze zijn opgenomen in het proces-verbaal van het hoofdstembureau.</p>
                    </section>

                    <section className="admitted-voters">
                        <h4 className="mb-2">Toegelaten kiezers</h4>
                        <VotesResume
                            votes={[
                                { name: 'Stempassen', count: 13500000 },
                                { name: 'Volmachtbewijzen', count: 500000 },
                                { name: 'Kiezerspassen', count: 89128 },
                                { name: 'Toegelaten kiezers', count: 13589128, bold: true },
                            ]}
                        />
                    </section>

                    <section className="votes-cast">
                        <h4 className="mb-2">Uitgebrachte stemmen</h4>
                        <p className="mb-4">
                            Klik op een partij om de stemmen per kandidaat te zien
                        </p>
                        <VotesList votes={VOTES_CAST_NEDERLAND} />
                    </section>

                    <VotesResume
                        votes={[
                            { name: 'Totaal stemmen op kandidaten', count: 10503656, bold: true },
                            { name: 'Blanco stemmen', count: 40128 },
                            { name: 'Ongeldige stemmen', count: 28206 },
                            { name: 'Totaal uitgebrachte stemmen', count: 10571990, bold: true },
                        ]}
                    />

                    <section id="processen-verbaal">
                        <ReportsWithResults
                            title="Processen-verbaal met resultaten"
                            description="Onderstaande documenten bevatten de laatste telresultaten van de kieskring, zoals ze worden meegeteld in de uitslag. De getallen in het overzicht hierboven komen uit het EML_NL tellingbestand."
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

                    <section id="uitleg">
                        <ResultsTimeline
                            title="Hoe zijn de resultaten tot stand gekomen?"
                            description="Het centraal stembureau (de Kiesraad) controleert de telresultaten van alle gemeenten en stembureaus. Als alles klopt worden de resultaten van alle gemeenten bij elkaar opgeteld, en wordt de uitslag vastgesteld."
                            steps={STEPS}
                        />
                    </section>

                    <IssueNotice id="fout-melden" reportHref={reportHref} />
                </div>

                <div>
                    <ResultsSourceBox
                        description="De telresultaten op deze pagina komen uit de uitslagensoftware. Dat zijn de resultaten die meetellen in de officiele uitslag. De gemeente heeft de resultaten gecontroleerd en vastgelegd in onderstaand proces-verbaal."
                        processHref="#processen-verbaal"
                        reportHref={reportHref}
                    />
                </div>
            </div>
        </Layout>
    )
}