import { Layout } from '../components/Layout.tsx'
import IssueReportWindowNotice from '../components/IssueReportWindowNotice.tsx'
import { PageQueryBoundary } from '../components/PageQueryBoundary.tsx'
import { useElectionConfigs } from '../hooks/queries.ts'

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
      <div className="page-main">
        <IssueReportWindowNotice
          opensAt={electionConfig.issue_report_opens_at}
          deadline={electionConfig.issue_report_deadline}
        />
      </div>
    </Layout>
  )
}
