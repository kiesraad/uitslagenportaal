import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUpRightFromSquare, faCheck } from '@fortawesome/free-solid-svg-icons'
import type { ReactNode } from 'react'
import { Layout } from '../components/Layout.tsx'
import PageTop from '../components/PageTop.tsx'
import IssueReportWindowNotice from '../components/IssueReportWindowNotice.tsx'
import { PageQueryBoundary } from '../components/PageQueryBoundary.tsx'
import { useElectionConfigs } from '../hooks/queries.ts'
import { formatDate } from '../utils/date.ts'
import { appRoutes } from '../utils/routes.ts'

export function ReportIssuePage() {
    const { data: electionConfigs, isLoading, isError, refetch } = useElectionConfigs()
    const electionConfig = electionConfigs?.[0]

    if (isLoading || isError || !electionConfig) {
        return (
            <PageQueryBoundary
                isLoading={isLoading}
                isError={isError || !electionConfig}
                onRetry={() => {
                    void refetch()
                }}
                entityLabel="Verkiezing"
            />
        )
    }

    return (
        <Layout title="Een fout melden">
            <PageTop
                title="Een fout melden"
                breadcrumb={[
                    { href: appRoutes.home(), label: 'Home' },
                    {
                        href: appRoutes.electionConfigMunicipalityList(electionConfig.slug),
                        label: electionConfig.label,
                    },
                    { href: appRoutes.reportIssue(), label: 'Stembureau' },
                ]}
            />
            <div className="page-main">
                <div className="page-space-3 max-w-2xl">
                    <p>
                        Denkt u dat er een fout is gemaakt bij het tellen, opschrijven of het overtypen
                        van de stemmen? Dan kunt u daar een melding van maken bij het centraal stembureau.
                    </p>

                    <IssueReportWindowNotice
                        opensAt={electionConfig.issue_report_opens_at}
                        deadline={electionConfig.issue_report_deadline}
                    />

                    <section className="flex flex-col gap-3">
                        <h2 className="text-xl font-bold font-title">Waarvoor kunt u een melding maken?</h2>
                        <p>
                            U kunt een melding maken van mogelijke fouten die zijn gemaakt bij het tellen,
                            opschrijven of overtypen van de stemmen in de uitslagensoftware. Dit kan voor
                            de processen-verbaal van het lokaal stembureau, het gemeentelijk stembureau,
                            het hoofdstembureau, het briefstembureau en het nationaal briefstembureau.
                        </p>
                    </section>

                    <section className="flex flex-col gap-3">
                        <h2 className="text-xl font-bold font-title">Wat wordt er met een melding gedaan?</h2>
                        <p>
                            Nadat we je melding hebben ontvangen, zoeken we uit wat er aan de hand is. Als dat
                            nodig is, nemen we contact op met de gemeente of het stembureau. In sommige gevallen
                            kan er een hertelling plaatsvinden. Als blijkt dat er inderdaad een fout is gemaakt,
                            bijvoorbeeld bij het tellen van de stemmen, dan wordt die fout hersteld. De correctie
                            wordt vastgelegd in een corrigendum en openbaar gemaakt door dit te publiceren. Je
                            ontvangt geen persoonlijk bericht over wat er met je melding is gedaan.
                        </p>
                    </section>

                    <section className="flex flex-col gap-3">
                        <h2 className="text-xl font-bold font-title">
                            Punten waar uw melding aan moet voldoen
                        </h2>
                        <ul className="flex flex-col gap-4 list-none p-0 m-0">
                            <ChecklistItem>
                                De melding moet voor {formatDate(electionConfig.issue_report_deadline)} bij de
                                Kiesraad binnen zijn.
                            </ChecklistItem>
                            <ChecklistItem>
                                De melding moet gaan over een mogelijke fout in het (op)tellen van de stemmen in het
                                proces-verbaal of in het digitale bestand van de gemeente. Andere klachten, zoals over
                                een stembureau dat te laat open was, horen thuis bij de zitting van het betreffende stembureau.
                            </ChecklistItem>
                            <ChecklistItem>
                                De melding moet duidelijk en onderbouwd zijn: geef aan wat er precies fout is gegaan, in welke gemeente of bij welk stembureau, en waar de fout in zit.
                            </ChecklistItem>
                            <ChecklistItem>
                                De melding moet gaan over iets wat u zelf heeft gezien of meegemaakt, niet over iets wat u van iemand anders heeft gehoord.
                            </ChecklistItem>
                            <ChecklistItem>Vermeld geen persoonsgegevens in uw melding; dat is niet nodig.</ChecklistItem>
                        </ul>
                    </section>

                    {electionConfig.report_error_url && (
                        <a
                            className="report-error-button"
                            href={electionConfig.report_error_url}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Meld een fout
                            <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
                        </a>
                    )}
                </div>
            </div>
        </Layout>
    )
}

function ChecklistItem({ children }: { children: ReactNode }) {
    return (
        <li className="flex items-start gap-2">
            <FontAwesomeIcon icon={faCheck} className="mt-1 size-4 shrink-0 text-[var(--c-done)]" />
            <span>{children}</span>
        </li>
    )
}
