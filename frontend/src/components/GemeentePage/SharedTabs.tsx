import { Link, matchPath, useLocation } from 'react-router-dom'

type Props = {
  tabs: {
    label: string
    value: string
    activePatterns?: string[]
  }[]
}

export default function SharedTabs({ tabs }: Props) {
  const location = useLocation()

  return (
    <div className="tabs">
      {tabs.map((tab) => {
        const patterns = tab.activePatterns ?? [tab.value]
        const isActive = patterns.some((pattern) =>
          matchPath(
            { path: pattern, end: !pattern.endsWith('*') },
            location.pathname,
          ),
        )

        return (
          <Link
            key={tab.value}
            to={tab.value}
            className={`tab${isActive ? ' active' : ''}`}
          >
            {tab.label}
          </Link>
        )
      })}
    </div>
  )
}
