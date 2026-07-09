import { Link } from 'react-router-dom'
import { InfoBox } from '../InfoBox'
import { faArrowRight, faMaximize } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

type Props = {
  description: string
  processHref?: string
  reportHref: string
}

export default function ResultsSourceBox({ description, processHref = '#', reportHref }: Props) {
  return (
    <div className="counting-results-infobox">
      <InfoBox>
        <h4>Waar komen deze telresultaten vandaan?</h4>
        <span className="mb-2">{description}</span>
        <div className="results-image-container mb-2">
          <div className="results-image-resize">
            <FontAwesomeIcon icon={faMaximize} />
          </div>
          <img src="/images/results_image.png" alt="Results image" className="mb-3 results-image" />
        </div>
        <p className="mb-3">
          <a href={processHref}>Bekijk het proces-verbaal <FontAwesomeIcon icon={faArrowRight} /></a>
        </p>
        <span className="mb-1">
          Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de
          stemmen. Fouten die na 14 december 10:00 worden gemeld, kunnen we nog
          onderzoeken en herstellen. Dan kan de juiste informatie mee in de
          officiele uitslag.
        </span>
        <p>
          <Link to={reportHref} className="bold">Meld een fout of iets dat niet klopt <FontAwesomeIcon icon={faArrowRight} /></Link>
        </p>
      </InfoBox>
    </div>
  )
}
