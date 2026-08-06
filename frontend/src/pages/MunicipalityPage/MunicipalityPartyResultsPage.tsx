import { useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Layout } from '../../components/Layout.tsx'
import PageTop from '../../components/PageTop.tsx'
import { PageQueryBoundary } from '../../components/PageQueryBoundary.tsx'
import { useElectionConfig, useRegion } from '../../hooks/queries.ts'
import { appRoutes } from '../../utils/routes.ts'

import IssueNotice from '../../components/ResultsPage/IssueNotice.tsx'
import CandidatesVoteList from '../../components/ResultsPage/CandidatesVoteList.tsx'
import PageIndex from '../../components/PageIndex'
import { formatDate } from '../../utils/date.ts'
import { getCsbCrumb } from '../../utils/region.ts'

export function MunicipalityPartyResultsPage() {
  const {
    electionConfigSlug: electionConfigSlugParam,
    regionSlug: parentRegionSlugParam,
    partySlug: partySlugParam,
    csbSlug: csbSlugParam,
  } = useParams<{ electionConfigSlug: string; regionSlug: string; partySlug: string; csbSlug?: string }>()

  const electionConfigSlug = decodeURIComponent(electionConfigSlugParam ?? '')
  const regionSlug = decodeURIComponent(parentRegionSlugParam ?? '')
  const partySlug = decodeURIComponent(partySlugParam ?? '')
  const csbSlug = csbSlugParam ? decodeURIComponent(csbSlugParam) : undefined

  const {
    data: electionConfig,
    isLoading: isElectionLoading,
    isError: isElectionError,
    refetch: refetchElection,
  } = useElectionConfig(electionConfigSlug)
  const {
    data: region,
    isLoading: isRegionLoading,
    isError: isRegionError,
    refetch: refetchRegion,
  } = useRegion(electionConfigSlug, regionSlug, csbSlug)

  const isLoading = isElectionLoading || isRegionLoading
  const isError = isElectionError || isRegionError || !electionConfig || !region

  const currentPartyVoteCounts = useMemo(
    () =>
      (region?.vote_counts.filter(
        (voteCount) => voteCount.party.slug === partySlug && voteCount.result_level === 'CANDIDATE',
      ) ?? []).sort((a, b) => (a.candidate?.position ?? 0) - (b.candidate?.position ?? 0)),
    [region?.vote_counts, partySlug],
  )

  const partyLevelVoteCounts = useMemo(
    () => region?.vote_counts.filter((voteCount) => voteCount.result_level === 'PARTY') ?? [],
    [region?.vote_counts],
  )

  const partyVoteCount = useMemo(
    () => partyLevelVoteCounts.find((voteCount) => voteCount.party.slug === partySlug),
    [partyLevelVoteCounts, partySlug],
  )

  const partyListNumber = partyVoteCount?.party.list_number

  const municipalityResultsRoute = appRoutes.municipalityResults(electionConfigSlug, regionSlug, csbSlug)
  const municipalityPartyResultsRoute = appRoutes.municipalityPartyResults(electionConfigSlug, regionSlug, partySlug, csbSlug)

  if (isLoading || isError) {
    return (
      <PageQueryBoundary
        isLoading={isLoading}
        isError={isError}
        onRetry={() => {
          void refetchElection()
          void refetchRegion()
        }}
        entityLabel="Gemeente"
      />
    )
  }

  const partyName = partyVoteCount?.party.registered_name ?? 'Lijst'
  const pageTitle = `Telresultaten gemeente\n${region.region_name}`

  return (
    <Layout
      title={`Telresultaten gemeente – ${region.region_name}`}
      description={`Telresultaten gemeente – ${region.region_name}`}
    >
      <PageTop
        title={pageTitle}
        subtitle={`Geplaatst op: ${formatDate(region.results_available_at)}`}
        breadcrumb={[
          { href: appRoutes.home(), label: 'Home' },
          { href: appRoutes.electionConfigMunicipalityList(electionConfigSlug), label: electionConfig.label },
          getCsbCrumb(region, electionConfigSlug),
          { href: municipalityResultsRoute, label: `Gemeente ${region.region_name}` },
          { href: municipalityPartyResultsRoute, label: partyName },
        ]}
      />
      <div className="page-main page-main-two-columns">
        <div className="page-space-3">
          <PageIndex
            links={[
              { label: <><span className="font-semibold">Telresultaten</span> zoals ze meetellen in de officiele uitslag</>, url: '#telresultaten' },
              { label: <span className="font-semibold">Hoe u een fout kunt melden</span>, url: '#fout-melden' },
            ]}
          />

          <section id="telresultaten">
            <h2 className="text-lg mb-4.5 font-medium">Telresultaten lijst {partyListNumber}</h2>
            <h3 className="party-level-title mb-2">{partyName}</h3>
            <CandidatesVoteList
              voteCounts={currentPartyVoteCounts}
              partyVote={partyVoteCount}
              partyListNumber={partyListNumber}
            />
          </section>

          <IssueNotice issueReportDeadline={electionConfig.issue_report_deadline} />
        </div>
      </div>
    </Layout>
  )
}
