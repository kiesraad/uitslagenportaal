import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { PageQueryBoundary } from '@/components/PageQueryBoundary'

function renderBoundary(props: Partial<Parameters<typeof PageQueryBoundary>[0]> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PageQueryBoundary
          isLoading={false}
          isError={true}
          onRetry={vi.fn()}
          entityLabel="Stembureau"
          {...props}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('PageQueryBoundary', () => {
  it('shows the not-found page when a query failed with a 404', () => {
    renderBoundary({ errors: [new ApiError('Request failed: Not Found', 404)] })

    expect(screen.getByRole('heading', { name: 'Pagina niet gevonden' })).toBeInTheDocument()
    expect(screen.queryByText('Opnieuw proberen')).not.toBeInTheDocument()
  })

  it('offers a retry when the failure is not a 404', () => {
    renderBoundary({ errors: [new ApiError('Request failed: Server Error', 500)] })

    expect(screen.getByText('Kan stembureau niet laden.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Opnieuw proberen' })).toBeInTheDocument()
  })

  it('shows the not-found page when only one of several queries 404s', () => {
    renderBoundary({ errors: [null, new ApiError('Request failed: Not Found', 404), null] })

    expect(screen.getByRole('heading', { name: 'Pagina niet gevonden' })).toBeInTheDocument()
  })

  it('keeps showing the loading state while a query is still in flight', () => {
    renderBoundary({
      isLoading: true,
      errors: [new ApiError('Request failed: Not Found', 404)],
    })

    expect(screen.getByText('Stembureau laden…')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Pagina niet gevonden' })).not.toBeInTheDocument()
  })
})
