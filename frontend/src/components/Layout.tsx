import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Header } from './Header'
import { Footer } from './Footer'

interface LayoutProps {
  children: ReactNode
  title?: string
  description?: string
}

export function Layout({ children, title, description }: LayoutProps) {
  useEffect(() => {
    if (title) document.title = `${title} – Kiesraad`
  }, [title])

  useEffect(() => {
    const el = document.querySelector('meta[name="description"]')
    if (el && description) el.setAttribute('content', description)
  }, [description])

  return (
    <>
      <Header />
      <main className="layout-main">{children}</main>
      <Footer />
    </>
  )
}
