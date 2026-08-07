import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Footer } from '@/components/Footer'
import type { ElectionConfig } from '@/api/types'

const electionConfig: ElectionConfig = {
  slug: 'ws2023',
  label: 'Waterschapsverkiezingen 2023',
  date: '2023-12-15T11:00:00',
  issue_report_deadline: '2026-12-14T10:00:00',
  csb_type: 'WATERSCHAP',
  report_error_url: 'https://example.test/melding',
  counting_info_url: 'https://example.test/telproces',
  voting_url: 'https://example.test/stemmen',
}

function mockElectionConfigs(configs: ElectionConfig[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(configs),
      } as Response),
    ),
  )
}

function renderFooter() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )

  return render(<Footer />, { wrapper })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Footer', () => {
  it('Renders the copyright notice with the current year', () => {
    mockElectionConfigs([])
    renderFooter()

    const currentYear = new Date().getFullYear()
    expect(screen.getByText(`© ${currentYear} Kiesraad`)).toBeInTheDocument()
  })

  it('Always links to Kiesraad.nl', () => {
    mockElectionConfigs([])
    renderFooter()

    expect(screen.getByRole('link', { name: /Kiesraad\.nl/ })).toHaveAttribute(
      'href',
      'https://www.kiesraad.nl/',
    )
  })

  it('Shows the election label and links when a single election is available', async () => {
    mockElectionConfigs([electionConfig])
    renderFooter()

    expect(
      await screen.findByRole('heading', { name: electionConfig.label }),
    ).toBeInTheDocument()

    expect(screen.getByRole('link', { name: /Melding maken/ })).toHaveAttribute(
      'href',
      electionConfig.report_error_url,
    )
    expect(screen.getByRole('link', { name: /Uitleg over telproces/ })).toHaveAttribute(
      'href',
      electionConfig.counting_info_url,
    )
    expect(screen.getByRole('link', { name: /Stemmen/ })).toHaveAttribute(
      'href',
      electionConfig.voting_url,
    )
  })

  it('Omits links whose url is not configured', async () => {
    mockElectionConfigs([{ ...electionConfig, counting_info_url: '', voting_url: '' }])
    renderFooter()

    expect(
      await screen.findByRole('heading', { name: electionConfig.label }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Uitleg over telproces/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Stemmen/ })).not.toBeInTheDocument()
  })
})
