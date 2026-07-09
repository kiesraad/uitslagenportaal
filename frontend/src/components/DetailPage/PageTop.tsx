import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

type Props = {
  title: string
  subtitle?: string
  breadcrumb?: {
    href: string
    label: string
  }[]
  tabs?: ReactNode
}

export default function PageTop({ title, subtitle, breadcrumb, tabs }: Props) {
  return (
    <div className="page-top">
      {breadcrumb ? (
        <nav className="breadcrumb" aria-label="Breadcrumb">
          {breadcrumb.map((item, index) => (
            <span key={`${item.href}-${item.label}`} className="breadcrumb-item">
              <Link to={item.href}>{item.label}</Link>
              {index < breadcrumb.length - 1 && <span className="breadcrumb-sep">{'>'}</span>}
            </span>
          ))}
        </nav>
      ) : null}

      <h1 className="page-title">
        {title.split('\n').map((line, i) => <span key={i}>{line}<br /></span>)}
      </h1>
      {subtitle && <p className="page-subtitle">{subtitle}</p>}

      {tabs || null}
    </div>
  )
}
