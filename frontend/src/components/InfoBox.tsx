import { faCircleInfo } from '@fortawesome/free-solid-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import type { ReactNode } from 'react'

interface InfoBoxProps {
  children: ReactNode;
  disableMargin?: boolean;
}

export function InfoBox({ children, disableMargin }: InfoBoxProps) {
  return (
    <div className={`result-info-box ${!disableMargin ? 'mb-9 mt-8' : ''}`}>
      <FontAwesomeIcon icon={faCircleInfo} color="#102e53"/>
      <div className="result-info-body">
        {children}
      </div>
    </div>
  )
}
