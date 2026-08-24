import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUpRightFromSquare, faCheck } from '@fortawesome/free-solid-svg-icons'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { twMerge } from 'tailwind-merge'
import type { ElectionConfig } from '../api/types.ts'
import { Layout } from '../components/Layout.tsx'
import { InfoBox } from '../components/InfoBox.tsx'
import { PageQueryBoundary } from '../components/PageQueryBoundary.tsx'
import { useElectionConfig } from '../hooks/queries.ts'
import {
  formatDate,
  formatIssueReportDeadlineHeading,
  getRemainingReportTime,
} from '../utils/date.ts'
import { appRoutes } from '../utils/routes.ts'

const DEADLINE_TICK_MS = 60_000

export function ReportIssuePage() {
  const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>()
  const {
    data: electionConfig,
    isLoading,
    isError,
    error,
    refetch,
  } = useElectionConfig(electionConfigSlug)

  if (isLoading || isError || !electionConfig) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError || !electionConfig}
        onRetry={() => {
          void refetch()
        }}
        entityLabel="Verkiezing"
        errors={[error]}
      />
    )
  }

  return (
    <ReportIssuePageContent
      electionConfig={electionConfig}
      electionConfigSlug={electionConfigSlug ?? ''}
    />
  )
}

function ReportIssuePageContent({
  electionConfig,
  electionConfigSlug,
}: {
  electionConfig: ElectionConfig
  electionConfigSlug: string
}) {
  const deadline = electionConfig.issue_report_deadline
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const tick = () => setNow(new Date())
    const intervalId = window.setInterval(tick, DEADLINE_TICK_MS)

    const deadlineTime = new Date(deadline).getTime()
    let timeoutId: number | undefined
    if (!Number.isNaN(deadlineTime)) {
      const msUntilDeadline = deadlineTime - Date.now()
      if (msUntilDeadline > 0) {
        timeoutId = window.setTimeout(tick, msUntilDeadline)
      }
    }

    return () => {
      window.clearInterval(intervalId)
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [deadline])

  const reportingOpen = getRemainingReportTime(deadline, now) !== null
  const heading = formatIssueReportDeadlineHeading(deadline, now)

  return (
    <Layout title="Een fout melden">
      <div className="page-main">
        <div className="page-space-3 max-w-2xl">
          <div>
            <nav className="breadcrumb" aria-label="Breadcrumb">
              <span className="breadcrumb-item">
                <Link to={appRoutes.home()}>Home</Link>
                <span className="breadcrumb-sep">{'>'}</span>
              </span>
              <span className="breadcrumb-item">
                <Link to={appRoutes.electionConfigMunicipalityList(electionConfigSlug)}>
                  {electionConfig.label}
                </Link>
                <span className="breadcrumb-sep">{'>'}</span>
              </span>
              <span className="breadcrumb-item">
                <Link to={appRoutes.reportIssue(electionConfigSlug)}>Fout melden</Link>
              </span>
            </nav>
            <h1 className="mb-3 text-3xl sm:text-4xl font-title font-bold">Een fout melden</h1>
          </div>

          <p>
            Denkt u dat er een fout is gemaakt bij het tellen, opschrijven of het overtypen van de
            stemmen? Dan kunt u daar een melding van maken bij het centraal stembureau.
          </p>

          <InfoBox>
            <h4 className="font-bold">{heading}</h4>
            <p>
              Een melding aan het centraal stembureau kan van{' '}
              {formatDate(electionConfig.issue_report_opens_at)} tot{' '}
              {formatDate(electionConfig.issue_report_deadline)} (uiterlijk 48 uur voor de zitting
              van het centraal stembureau). Meldingen die later binnenkomen worden niet in
              behandeling genomen.
            </p>
          </InfoBox>

          <section className="flex flex-col gap-3">
            <h2>Waarvoor kunt u een melding maken?</h2>
            <p>
              U kunt een melding maken van mogelijke fouten die zijn gemaakt bij het tellen,
              opschrijven of overtypen van de stemmen in de uitslagensoftware. Dit kan voor de
              processen-verbaal van het lokaal stembureau, het gemeentelijk stembureau, het
              hoofdstembureau, het briefstembureau en het nationaal briefstembureau.
            </p>
          </section>

          <section className="flex flex-col gap-3">
            <h2>Wat wordt er met een melding gedaan?</h2>
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
            <h2>Punten waar uw melding aan moet voldoen</h2>
            <ul className="flex flex-col gap-4 list-none p-0 m-0">
              <ChecklistItem>
                De melding moet voor {formatDate(electionConfig.issue_report_deadline)} bij de
                Kiesraad binnen zijn.
              </ChecklistItem>
              <ChecklistItem>
                De melding moet gaan over een mogelijke fout in het (op)tellen van de stemmen in het
                proces-verbaal of in het digitale bestand van de gemeente. Andere klachten, zoals over
                een stembureau dat te laat open was, horen thuis bij de zitting van het betreffende
                stembureau.
              </ChecklistItem>
              <ChecklistItem>
                De melding moet duidelijk en onderbouwd zijn: geef aan wat er precies fout is gegaan,
                in welke gemeente of bij welk stembureau, en waar de fout in zit.
              </ChecklistItem>
              <ChecklistItem>
                De melding moet gaan over iets wat u zelf heeft gezien of meegemaakt, niet over iets
                wat u van iemand anders heeft gehoord.
              </ChecklistItem>
              <ChecklistItem>
                Vermeld geen persoonsgegevens in uw melding; dat is niet nodig.
              </ChecklistItem>
            </ul>
          </section>

          {electionConfig.report_error_url && (
            <a
              className={twMerge(
                'report-error-button',
                !reportingOpen && 'report-error-button-disabled',
              )}
              href={reportingOpen ? electionConfig.report_error_url : undefined}
              target={reportingOpen ? '_blank' : undefined}
              rel={reportingOpen ? 'noopener noreferrer' : undefined}
              aria-disabled={!reportingOpen}
              onClick={reportingOpen ? undefined : (event) => event.preventDefault()}
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
      <FontAwesomeIcon icon={faCheck} className="mt-1 size-4 shrink-0 text-(--c-done)" />
      <span>{children}</span>
    </li>
  )
}
