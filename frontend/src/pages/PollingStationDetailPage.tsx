import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
// import VOTES_CAST_POLLING_STATION from '../data/votecount_data/votes_cast_polling_station.json'
import IssueNotice from '../components/PollingStationDetailPage/IssueNotice'
import PageTop from '../components/DetailPage/PageTop'
import ReportsWithResults from '../components/DetailPage/ReportsWithResults'
// import ResultsSourceBox from '../components/PollingStationDetailPage/ResultsSourceBox'
import ResultsTimeline from '../components/PollingStationDetailPage/ResultsTimeline'
import VotesList from '../components/DetailPage/VotesList'
import VotesResume from '../components/PollingStationDetailPage/VotesResume'
import { Layout } from '../components/Layout'
// import POLLING_STATION_TIMELINE_STEPS from '../data/timeline_data/polling_station_timeline.json'
import { useElectionConfig, useRegion, useRegions } from '../hooks/queries'
import { appRoutes } from '../utils/routes'
import PageIndex from '../components/PageIndex'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faFile } from '@fortawesome/free-solid-svg-icons'

import type { Step } from '../components/Timeline'

export default function PollingStationDetailPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    parentRegionSlug: parentRegionSlugParam,
    pollingStationSlug: pollingStationSlugParam,
  } = useParams<{ electionConfigSlug: string; parentRegionSlug: string; pollingStationSlug: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const parentRegionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const pollingStationSlug = decodeURIComponent(pollingStationSlugParam ?? '')

  const { data: electionConfig, isLoading: isElectionLoading } = useElectionConfig(electionConfigSlug)
  const { data: region, isLoading: isRegionLoading, isError: isRegionError, refetch } = useRegion(electionConfigSlug, parentRegionSlug)
  const { data: pollingStation, isLoading: isPollingStationLoading } = useRegion(electionConfigSlug, pollingStationSlug)

  const partyLevelVoteCounts = useMemo(
    () => pollingStation?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [pollingStation?.vote_counts],
  )

  const municipalityDetailRoute = appRoutes.municipalityDetail(electionConfigSlug, parentRegionSlug)
  const pollingStationDetailRoute = appRoutes.pollingStationDetail(electionConfigSlug, parentRegionSlug, pollingStationSlug)
  const reportHref = appRoutes.reportError(parentRegionSlug, pollingStationSlug)

  // const pollingStationVotes = useMemo(
  //   () =>
  //     VOTES_CAST_POLLING_STATION.lijsttotalen.map((vote) => ({
  //       ...vote,
  //       // url: appRoutes.partyLevel(parentRegionSlug, pollingStationSlug, vote.name),
  //     })),
  //   [parentRegionSlug, pollingStationSlug],
  // )

  const pageTitle = pollingStation
    ? `Telresultaten stembureau\n${pollingStation.region_name}`
    : 'Telresultaten stembureau'

  if (isElectionLoading || isRegionLoading || isPollingStationLoading) {
    return (
      <Layout title="Stembureau laden…" description="Stembureau laden…">
        <p>Stembureau laden…</p>
      </Layout>
    )
  }

  if (isRegionError || !region) {
    return (
      <Layout title="Stembureau niet gevonden" description="Kan stembureau niet laden.">
        <p>Kan stembureau niet laden.</p>
        <button type="button" onClick={() => refetch()}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  if (!pollingStation) {
    return (
      <Layout title="Stembureau niet gevonden" description="Stembureau niet gevonden.">
        <p>Stembureau niet gevonden.</p>
      </Layout>
    )
  }

  return (
    <Layout
      title={`Telresultaten stembureau – ${pollingStation.region_name}`}
      description={`Telresultaten stembureau – ${pollingStation.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle="Geplaatst op: 10 december 2025 - 12:17"
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigDetailMunicipality(electionConfigSlug), label: electionConfig?.label ?? 'Verkiezing laden…' },
          { href: municipalityDetailRoute, label: `Gemeente ${region.region_name}` },
          { href: pollingStationDetailRoute, label: pollingStation.region_name },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="bold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <><span className="bold">Processen-verbaal</span> de officiele documenten van het stembureau</>, url: '#processen-verbaal' },
              { label: <><span className="bold">Uitleg</span> hoe deze resultaten tot stand zijn gekomen</>, url: '#uitleg' },
              { label: <span className="bold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h3 className="mb-2">Telresultaten</h3>
            <p>De gemeente typt de telgegevens van alle stembureaus over in de uitslagensoftware. Zo kunnen alle stemmen worden opgeteld. Hieronder zie je hoe de gegevens van dit stembureau zijn overgenomen in de uitslagensoftware.</p>
          </section>

          <section className="admitted-voters">
            <h4 className="mb-2">Toegelaten kiezers</h4>
            <VotesResume
              votes={[
                { name: 'Stempassen', count: 855 },
                { name: 'Volmachtbewijzen', count: 15 },
                { name: 'Kiezerspassen', count: 4 },
                { name: 'Toegelaten kiezers', count: 874, bold: true },
              ]}
            />
          </section>

          <section className="votes-cast">
            <h4 className="mb-2">Uitgebrachte stemmen</h4>
            <p className="mb-4">Klik op een lijst om de stemmen per kandidaat te zien</p>
            <VotesList voteCounts={partyLevelVoteCounts} />
          </section>

          <VotesResume
            votes={[
              { name: 'Totaal stemmen op kandidaten', count: 867, bold: true },
              { name: 'Blanco stemmen', count: 2 },
              { name: 'Ongeldige stemmen', count: 4 },
              { name: 'Totaal uitgebrachte stemmen', count: 873, bold: true },
            ]}
          />

          {/* <section id="processen-verbaal">
            <ReportsWithResults
              title="Processen-verbaal met resultaten"
              subtitle={pollingStation.region_name}
              description="De getallen hierboven laten zien hoe de resultaten van dit stembureau worden meegeteld in de uitslag. Ze komen uit de uitslagensoftware. Ze zijn door de gemeente overgetypt uit onderstaande documenten."
              files={[
                {
                  name: 'Proces-verbaal Na 31-2 bijlage 1 van stembureau 18',
                  icon: (
                    <FontAwesomeIcon icon={faFile} />
                  ),
                  url: '#',
                  type: 'PDF',
                  size: '3 MB',
                  description: 'Handgeschreven telresultaten. Telling per lijst en kandidaat door het gemeentelijk stembureau. Bron voor de officiele resultaten.',
                },
                {
                  name: 'Proces-verbaal Na 10-2 van stembureau 18',
                  type: 'PDF',
                  icon: (
                    <FontAwesomeIcon icon={faFile} />
                  ),
                  url: '#',
                  size: '2.4 MB',
                  description: 'Handgeschreven telresultaten. Sneltelling per lijst op het stembureau, geen officiele resultaten.',
                },
              ]}
            />
          </section> */}

          {/* <section id="uitleg">
            <ResultsTimeline
              title="Hoe zijn de resultaten tot stand gekomen?"
              description="In deze gemeente is gekozen voor centrale stemopneming. Het stembureau doet een sneltelling per partij. Het gemeentelijk stembureau telt de volgende dag alles nog een keer na en telt de stemmen per kandidaat op een centrale tellocatie."
              // steps={POLLING_STATION_TIMELINE_STEPS as Step[]}
            />
          </section> */}

          <IssueNotice id="fout-melden" reportHref={reportHref} />
        </div>
        {/* <div>
          <ResultsSourceBox
            description="De telresultaten op deze pagina komen uit de uitslagensoftware. Ze zijn overgetypt uit het proces-verbaal dat gemaakt is na het tellen van de stemmen."
            processHref="#processen-verbaal"
            reportHref={reportHref}
          />
        </div> */}
      </div>
    </Layout>
  )
}
