import type {ReactNode} from 'react'
import {Header} from './Header'
import {Footer} from './Footer'
import HtmlHead from "@/components/HtmlHead.tsx";

interface LayoutProps {
  children: ReactNode
  title?: string
  description?: string
}

export function Layout({children, title, description}: LayoutProps) {
  return (
    <>
      <HtmlHead title={title} description={description} />
      <Header/>
      <main className="layout-main">{children}</main>
      <Footer/>
    </>
  )
}
