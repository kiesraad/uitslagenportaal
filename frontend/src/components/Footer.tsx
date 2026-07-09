import { faArrowUpRightFromSquare, faChevronRight } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome"

function ExternalLinkIcon() {
  return (
    <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
  )
}

export function Footer() {
  const currentYear = new Date().getFullYear()

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
              <a href="#">
                <FontAwesomeIcon icon={faChevronRight} />
                Melding maken
              </a>
            </div>
            <div className="footer-col">
              <h4>Tweede Kamerverkiezing</h4>
              <a href="#">
                <ExternalLinkIcon />
                Uitleg over telproces
              </a>
              <a href="#">
                <ExternalLinkIcon />
                Stemmen
              </a>
              <a href="#">
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
