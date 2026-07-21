import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Footer } from '@/components/Footer'

describe('Footer', () => {
  it('renders the copyright notice with the current year', () => {
    render(<Footer />)

    const currentYear = new Date().getFullYear()
    expect(screen.getByText(`© ${currentYear} Kiesraad`)).toBeInTheDocument()
  })
})
