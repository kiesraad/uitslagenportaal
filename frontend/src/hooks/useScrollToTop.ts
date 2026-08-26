import { useEffect } from 'react'
import { useLocation, useNavigationType } from 'react-router'

// Used to scroll to top on some pages
export function useScrollToTop() {
  const { pathname } = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    if (navigationType === 'POP') return

    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname, navigationType])
}
