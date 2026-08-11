import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { ElectionConfig } from '@/api/types'
import { useElectionConfig } from '@/hooks/queries'
import { ReportIssuePage } from '@/pages/ReportIssuePage'

vi.mock('@/hooks/queries', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/queries')>()
  return {
    ...actual,
    useElectionConfig: vi.fn(),
  }
})

const electionConfig: ElectionConfig = {
  slug: 'ws2023',
  label: 'Waterschapsverkiezingen 2023',
  date: '2023-12-15T11:00:00',
  issue_report_opens_at: '2026-12-08T09:00:00',
  issue_report_deadline: '2026-12-10T12:45:00+01:00',
  csb_type: 'WATERSCHAP',
  report_error_url: 'https://example.test/melding',
  counting_info_url: 'https://example.test/telproces',
  voting_url: 'https://example.test/stemmen',
}

function mockUseElectionConfig(data: ElectionConfig) {
  vi.mocked(useElectionConfig).mockReturnValue({
    data,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useElectionConfig>)
}

function renderReportIssuePage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/ws2023/fout-melden']}>
        <Routes>
          <Route path="/:electionConfigSlug/fout-melden" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )

  return render(<ReportIssuePage />, { wrapper })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-12-10T12:00:00+01:00'))
  mockUseElectionConfig(electionConfig)
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ReportIssuePage', () => {
  it('updates the deadline heading as time passes', () => {
    renderReportIssuePage()

    expect(
      screen.getByRole('heading', { name: 'U heeft nog 45 minuten om een melding te maken' }),
    ).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(60_000)
    })

    expect(
      screen.getByRole('heading', { name: 'U heeft nog 44 minuten om een melding te maken' }),
    ).toBeInTheDocument()
  })

  it('disables the report button when the deadline passes', () => {
    mockUseElectionConfig({
      ...electionConfig,
      issue_report_deadline: '2026-12-10T12:00:30+01:00',
    })

    renderReportIssuePage()

    expect(screen.getByText('Meld een fout')).not.toHaveAttribute('aria-disabled', 'true')

    act(() => {
      vi.advanceTimersByTime(30_000)
    })

    expect(
      screen.getByRole('heading', { name: 'U kunt geen fout meer melden' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Meld een fout')).toHaveAttribute('aria-disabled', 'true')
  })
})
