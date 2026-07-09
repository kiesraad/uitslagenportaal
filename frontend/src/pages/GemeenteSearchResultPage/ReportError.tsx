import { useParams } from 'react-router-dom'
import { InfoBox } from '../../components/InfoBox'
import { PlatformLayout } from '../../components/PlatformLayout'
import { PlatformPageTop } from '../../components/PlatformPageTop'
import { appRoutes } from '../../utils/routes'
import { faArrowUpRightFromSquare, faCheck } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'

export default function ReportError() {
  const { gemeente: gemeenteParam, stembureau: stembureauParam } = useParams<{ gemeente: string; stembureau?: string }>()
  const gemeente = decodeURIComponent(gemeenteParam ?? '')
  const stembureau = stembureauParam ? decodeURIComponent(stembureauParam) : null

  return (
    <PlatformLayout
      title="Een fout melden"
      description="Meld een fout in het telproces"
    >
      <div className="platform-page-shell report-error-shell">
        <PlatformPageTop
          title="Een fout melden"
          breadcrumb={[
            { href: appRoutes.home(), label: 'Home' },
            { href: appRoutes.municipalitySearch(), label: 'Tweede Kamerverkiezing 2025' },
            { href: appRoutes.municipality(gemeente), label: `Gemeente ${gemeente}` },
            ...(stembureau
              ? [
                  {
                    href: appRoutes.pollingStationResults(gemeente, stembureau),
                    label: stembureau,
                  },
                ]
              : []),
          ]}
        />

        <div className="report-error-page">
          <p className="report-error-intro">
            Denkt u dat er een fout is gemaakt bij het tellen, opschrijven of het overtypen van de
            stemmen? Dan kunt u daar een melding van maken bij het centraal stembureau.
          </p>

          <InfoBox disableMargin>
            <div className="report-error-deadline">
              <strong>U heeft nog 3 dagen om een melding te maken</strong>
              <span>
                Een melding aan het centraal stembureau kan van maandag 8 december 2025 vanaf
                09.00 uur tot woensdag 14 december 2025 10.00 uur (uiterlijk 48 uur voor de
                zitting van het centraal stembureau). Meldingen die later binnenkomen worden niet
                in behandeling genomen.
              </span>
            </div>
          </InfoBox>

          <section className="report-error-section">
            <h2 className="report-error-section-title">Waarvoor kunt u een melding maken?</h2>
            <p>
              U kunt een melding maken van mogelijke fouten die zijn gemaakt bij het tellen,
              opschrijven of overtypen van de stemmen in de uitslagensoftware. Dit kan voor het
              proces-verbaal van het lokaal stembureau, het gemeentelijk stembureau, het
              hoofdstembureau, het briefstembureau en het nationaal briefstembureau.
            </p>
          </section>

          <section className="report-error-section">
            <h2 className="report-error-section-title">Wat wordt er met een melding gedaan?</h2>
            <p>
              Nadat we je melding hebben ontvangen, zoeken we uit wat er aan de hand is. Als dat
              nodig is, nemen we contact op met de gemeente of het stembureau. In sommige gevallen
              kan er een hertelling plaatsvinden. Als blijkt dat er inderdaad een fout is gemaakt,
              bijvoorbeeld bij het tellen van de stemmen, dan wordt die fout hersteld. De
              correctie wordt vastgelegd in een corrigendum en openbaar gemaakt door dit te
              publiceren. Je ontvangt geen persoonlijk bericht over wat er met je melding is
              gedaan.
            </p>
          </section>

          <section className="report-error-section">
            <h2 className="report-error-section-title">
              Punten waar uw melding aan moet voldoen
            </h2>
            <ul className="report-error-checklist">
              <CheckListItem text="De melding moet voor woensdag 14 december 2025 om 10.00 uur bij de Kiesraad binnen zijn." />
              <CheckListItem text="De melding moet gaan over een mogelijke fout in het (op)tellen van de stemmen in het proces-verbaal of in het digitale bestand van de gemeente." />
              <CheckListItem text="De melding moet duidelijk en onderbouwd zijn: geef aan wat er precies fout is gegaan, in welke gemeente of bij welk stembureau, en waar de fout in zit." />
              <CheckListItem text="De melding moet gaan over iets wat u zelf heeft gezien of meegemaakt, niet over iets wat u van iemand anders heeft gehoord." />
              <CheckListItem text="Vermeld geen persoonsgegevens in uw melding; dat is niet nodig." />
            </ul>
          </section>

          <a href="#" className="report-error-button">
            <span>Meld een fout</span>
            <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
          </a>
        </div>
      </div>
    </PlatformLayout>
  )
}

type Props = {
  text: string;
}
function CheckListItem({ text }: Props) {
  return (
    <div className="report-error-checklist-item">
      <FontAwesomeIcon icon={faCheck} color='green' />
      <p className="report-error-checklist-item-text">{text}</p>
    </div>
  )
}
