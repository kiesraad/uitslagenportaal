import { Layout } from './Layout'

type PageQueryBoundaryProps = {
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  entityLabel: string
}

/**
 * Full-page loading / error gate for query-backed pages.
 * Use as an early return when `isLoading || isError`.
 */
export function PageQueryBoundary({
  isLoading,
  isError,
  onRetry,
  entityLabel,
}: PageQueryBoundaryProps) {
  const labelLower = entityLabel.toLowerCase()

  if (isLoading) {
    return (
      <Layout title={`${entityLabel} laden…`} description={`${entityLabel} laden…`}>
        <p>{labelLower} laden…</p>
      </Layout>
    )
  }

  if (isError) {
    return (
      <Layout
        title={`${entityLabel} niet gevonden`}
        description={`Kan ${labelLower} niet laden.`}
      >
        <p>Kan {labelLower} niet laden.</p>
        <button type="button" onClick={onRetry}>
          Opnieuw proberen
        </button>
      </Layout>
    )
  }

  return null
}
