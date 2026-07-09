import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Footer } from './Footer'
import { Header } from './Header'

interface PlatformLayoutProps {
  children: ReactNode
  title?: string
  description?: string
}

export function PlatformLayout({ children, title, description }: PlatformLayoutProps) {
  useEffect(() => {
    if (title) document.title = `${title} - Kiesraad`
  }, [title])

  useEffect(() => {
    const el = document.querySelector('meta[name="description"]')
    if (el && description) el.setAttribute('content', description)
  }, [description])

  return (
    <>
      <Header />
      <main className="platform-layout-main">{children}</main>
      <Footer />
    </>
  )
}
