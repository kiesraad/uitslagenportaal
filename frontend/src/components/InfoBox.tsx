import type { ReactNode } from 'react'

interface InfoBoxProps {
  children: ReactNode;
  disableMargin?: boolean;
}

export function InfoBox({ children, disableMargin }: InfoBoxProps) {
  return (
    <div className={`result-info-box ${!disableMargin ? 'mb-9 mt-8' : ''}`}>
      <i className="result-info-icon" aria-hidden="true">i</i>
      <div className="result-info-body">
        {children}
      </div>
    </div>
  )
}
