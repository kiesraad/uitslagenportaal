import { faArrowUpRightFromSquare, faChevronRight } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"
import { useParams } from "react-router"
import { useElectionConfig, useElectionConfigs } from "../hooks/queries.ts"

const KIESRAAD_URL = "https://www.kiesraad.nl/"

function ExternalLinkIcon() {
  return (
    <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
  )
}

export function Footer() {
  const currentYear = new Date().getFullYear()
  const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>()

  // On election pages the config comes from the route; elsewhere (e.g. the home
  // page) fall back to the only election when there is exactly one.
  const { data: routeElectionConfig } = useElectionConfig(electionConfigSlug)
  const { data: electionConfigs } = useElectionConfigs()
  const electionConfig =
    routeElectionConfig ?? (electionConfigs?.length === 1 ? electionConfigs[0] : undefined)

  const label = electionConfig?.label
  const reportErrorUrl = electionConfig?.report_error_url
  const countingInfoUrl = electionConfig?.counting_info_url
  const votingUrl = electionConfig?.voting_url

  return (
    <footer className="footer">
      <div className="footer-navy">
        <div className="footer-top">
          <div className="footer-logo">
            <div className="footer-logo-left">
              <div className="f-logo-grid-v-container">
                <img src="/footer_logo.png" alt="Kiesraad" className="footer-logo-img" />
                <div className="f-logo-grid-v">
                  <div className="f-logo-grid-item">
                    <div className="f-logo-grid-item-bullet"></div>
                    <div className="f-logo-grid-item-bullet"></div>
                  </div>
                  <div className="f-logo-grid-item"></div>
                </div>
              </div>
              <div className="f-logo-grid-h">
                {Array.from({ length: 5 }).map((_, index) => (
                  <div key={index} className="f-logo-grid-item">
                    <div className="f-logo-grid-item-bullet"></div>
                    <div className="f-logo-grid-item-bullet"></div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div className="footer-right">
            <div className="footer-col">
              <h4>Zie je een fout?</h4>
              {reportErrorUrl && (
                <a href={reportErrorUrl} target="_blank" rel="noopener noreferrer">
                  <FontAwesomeIcon icon={faChevronRight} />
                  Melding maken
                </a>
              )}
            </div>
            <div className="footer-col">
              {label && <h4>{label}</h4>}
              {countingInfoUrl && (
                <a href={countingInfoUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLinkIcon />
                  Uitleg over telproces
                </a>
              )}
              {votingUrl && (
                <a href={votingUrl} target="_blank" rel="noopener noreferrer">
                  <ExternalLinkIcon />
                  Stemmen
                </a>
              )}
              <a href={KIESRAAD_URL} target="_blank" rel="noopener noreferrer">
                <ExternalLinkIcon />
                Kiesraad.nl
              </a>
            </div>
          </div>
        </div>

        <div className="footer-meta">
          <div>
            <p className="footer-tagline">
              Verkiezingen waar de samenleving op kan vertrouwen
            </p>
            <p className="footer-collab">In samenwerking met de Kiesraad</p>
          </div>
          <span className="footer-copy">© {currentYear} Kiesraad</span>
        </div>
      </div>

      <div className="footer-lang">
        <div className="footer-lang-inner">
          <p className="footer-lang-label">Deze website in andere talen:</p>
          <button className="footer-lang-btn" type="button">English</button>
        </div>
      </div>
    </footer>
  )
}
