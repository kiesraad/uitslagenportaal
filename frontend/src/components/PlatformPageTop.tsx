import { Link } from 'react-router-dom'

interface PlatformBreadcrumbItem {
  href: string
  label: string
}

interface PlatformPageTopProps {
  title: string
  breadcrumb?: PlatformBreadcrumbItem[]
}

export function PlatformPageTop({ title, breadcrumb }: PlatformPageTopProps) {
  return (
    <div className="platform-page-top">
      {breadcrumb ? (
        <nav className="platform-breadcrumb" aria-label="Breadcrumb">
          {breadcrumb.map((item, index) => (
            <span key={`${item.href}-${item.label}`} className="platform-breadcrumb-item">
              <Link to={item.href}>{item.label}</Link>
              {index < breadcrumb.length - 1 && (
                <span className="platform-breadcrumb-sep">{'>'}</span>
              )}
            </span>
          ))}
        </nav>
      ) : null}

      <h1 className="platform-page-title">
        {title.split('\n').map((line, index) => (
          <span key={index}>
            {line}
            <br />
          </span>
        ))}
      </h1>
    </div>
  )
}
