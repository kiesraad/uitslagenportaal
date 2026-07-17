import { Link } from 'react-router-dom'
import { InfoBox } from '../InfoBox'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowRight } from '@fortawesome/free-solid-svg-icons'


export default function IssueNotice() {
  return (
    <section id='fout-melden'>
      <InfoBox>
        <h4>Klopt er iets niet?</h4>
        <span>
          Soms gaat er iets mis bij het tellen, opschrijven of overtypen van de
          stemmen. Fouten die na 14 december 10:00 worden gemeld, kunnen we nog
          onderzoeken en herstellen. Dan kan de juiste informatie mee in de
          officiele uitslag.
        </span>
        <p>
          <Link to={'https://www.kiesraad.nl/'}>Meld een fout of iets dat niet klopt<FontAwesomeIcon icon={faArrowRight} /></Link>
        </p>
      </InfoBox>
    </section>
  )
}
