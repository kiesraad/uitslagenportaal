import { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import resultsTableData from '../assets/results_table_nederland.json'
import './ResultsTable.css'

type VoteColumnKey =
  | 'total'
  | 'kieskring1'
  | 'kieskring2'
  | 'kieskring3'
  | 'kieskring4'
  | 'kieskring5'
  | 'kieskring6'
  | 'kieskring7'
  | 'kieskring8'

type CandidateResultRow = {
  position: number
  candidate: string
  votes: Record<VoteColumnKey, number>
}

type ResultsTableData = {
  rows: CandidateResultRow[]
  totals: Record<VoteColumnKey, number>
}

const VOTE_COLUMNS: { key: VoteColumnKey; label: string; isTotal?: boolean }[] = [
  { key: 'total', label: 'Totaal', isTotal: true },
  { key: 'kieskring1', label: 'kieskring 1' },
  { key: 'kieskring2', label: 'kieskring 2' },
  { key: 'kieskring3', label: 'kieskring 3' },
  { key: 'kieskring4', label: 'kieskring 4' },
  { key: 'kieskring5', label: 'kieskring 5' },
  { key: 'kieskring6', label: 'kieskring 6' },
  { key: 'kieskring7', label: 'kieskring 7' },
  { key: 'kieskring8', label: 'kieskring 8' },
]

const data = resultsTableData as ResultsTableData
const numberFormatter = new Intl.NumberFormat('nl-NL', {
  maximumFractionDigits: 0,
})

export default function ResultsTable() {
  const topScrollRef = useRef<HTMLDivElement>(null)
  const tableScrollRef = useRef<HTMLDivElement>(null)
  const [hasScroll, setHasScroll] = useState(false)
  const [hasRightScroll, setHasRightScroll] = useState(false)

  const updateScrollState = useCallback(() => {
    const scrollElement = tableScrollRef.current

    if (!scrollElement) return

    const canScroll = scrollElement.scrollWidth > scrollElement.clientWidth + 1
    const canScrollRight =
      canScroll &&
      scrollElement.scrollLeft + scrollElement.clientWidth < scrollElement.scrollWidth - 1

    setHasScroll(canScroll)
    setHasRightScroll(canScrollRight)
  }, [])

  const syncScroll = useCallback(
    (source: 'top' | 'table') => {
      const topScroll = topScrollRef.current
      const tableScroll = tableScrollRef.current

      if (!topScroll || !tableScroll) return

      if (source === 'top' && tableScroll.scrollLeft !== topScroll.scrollLeft) {
        tableScroll.scrollLeft = topScroll.scrollLeft
      }

      if (source === 'table' && topScroll.scrollLeft !== tableScroll.scrollLeft) {
        topScroll.scrollLeft = tableScroll.scrollLeft
      }

      updateScrollState()
    },
    [updateScrollState],
  )

  useEffect(() => {
    const scrollElement = tableScrollRef.current

    if (!scrollElement) return

    updateScrollState()

    const resizeObserver = new ResizeObserver(updateScrollState)
    resizeObserver.observe(scrollElement)
    window.addEventListener('resize', updateScrollState)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateScrollState)
    }
  }, [updateScrollState])

  const tableStyles = {
    '--results-table-scroll-width': `${VOTE_COLUMNS.length * 8.65}rem`,
    '--results-table-column-count': VOTE_COLUMNS.length,
  } as CSSProperties

  return (
    <div
      className={[
        'results-table',
        hasScroll ? 'results-table-has-scroll' : '',
        hasRightScroll ? 'results-table-has-right-scroll' : '',
      ].filter(Boolean).join(' ')}
      role="table"
      aria-label="Telresultaten per kandidaat en kieskring"
      style={tableStyles}
    >
      <div className="results-table-candidate-pane">
        <div className="results-table-top-spacer" aria-hidden="true" />
        <div className="results-table-header-cell" role="columnheader">
          Kandidaat
        </div>

        <div role="rowgroup">
          {data.rows.map((row, index) => (
            <div
              className={`results-table-row results-table-candidate-row ${index % 2 === 0 ? 'results-table-row-alt' : ''}`}
              role="row"
              key={`${row.position}-${row.candidate}`}
            >
              <span className="results-table-position">{row.position}</span>
              <span className="results-table-candidate-name">{row.candidate}</span>
            </div>
          ))}
        </div>

        <div className="results-table-total-row results-table-candidate-total" role="row">
          <span>Totaal</span>
        </div>
      </div>

      <div className="results-table-values-pane">
        <div
          className="results-table-top-scroll"
          ref={topScrollRef}
          onScroll={() => syncScroll('top')}
          aria-hidden="true"
        >
          <div className="results-table-scroll-sizer" />
        </div>

        <div
          className="results-table-values-scroll"
          ref={tableScrollRef}
          onScroll={() => syncScroll('table')}
        >
          <div className="results-table-values-grid results-table-values-header" role="row">
            {VOTE_COLUMNS.map((column) => (
              <div className="results-table-header-cell" role="columnheader" key={column.key}>
                {column.label}
              </div>
            ))}
          </div>

          <div role="rowgroup">
            {data.rows.map((row, index) => (
              <div
                className={`results-table-values-grid results-table-row ${index % 2 === 0 ? 'results-table-row-alt' : ''}`}
                role="row"
                key={`${row.position}-${row.candidate}-values`}
              >
                {VOTE_COLUMNS.map((column) => (
                  <span
                    className={`results-table-value ${column.isTotal ? 'results-table-value-total' : ''}`}
                    role="cell"
                    key={`${row.position}-${column.key}`}
                  >
                    {numberFormatter.format(row.votes[column.key])}
                  </span>
                ))}
              </div>
            ))}
          </div>

          <div className="results-table-values-grid results-table-total-row" role="row">
            {VOTE_COLUMNS.map((column) => (
              <span className="results-table-value results-table-value-total" role="cell" key={column.key}>
                {numberFormatter.format(data.totals[column.key])}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
