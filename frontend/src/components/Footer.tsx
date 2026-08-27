import { faArrowUpRightFromSquare, faChevronRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLingui } from "@lingui/react";
import { Trans } from "@lingui/react/macro";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { type Locale, loadCatalog, localeDisplayName, resolveLocale, saveLocale } from "@/i18n";
import { electionConfigQuery, useElectionConfigs } from "../hooks/queries.ts";

// Fixed URLs for non-changing elements
const KIESRAAD_URL = "https://www.kiesraad.nl/";
const REPORT_ERROR_URL = "https://www.kiesraad.nl/service/contact";

function LanguageSwitcher() {
   // Reading the locale through the hook (rather than the imported singleton)
   // is what subscribes this component to locale changes.
   const { i18n } = useLingui();
   const current: Locale = resolveLocale(i18n.locale);
   const other: Locale = current === "nl" ? "en" : "nl";

   async function switchTo(locale: Locale) {
      saveLocale(locale);
      await loadCatalog(locale);
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
   }

   return (
      <div className="footer-lang">
         <div className="footer-lang-inner">
            <p className="footer-lang-label">
               <Trans>Deze website in andere talen:</Trans>
            </p>
            <button className="footer-lang-btn" type="button" lang={other} onClick={() => switchTo(other)}>
               {localeDisplayName(other)}
            </button>
         </div>
      </div>
   );
}

function ExternalLinkIcon() {
   return <FontAwesomeIcon icon={faArrowUpRightFromSquare} />;
}

export function Footer() {
   const currentYear = new Date().getFullYear();
   const { electionConfigSlug } = useParams<{ electionConfigSlug: string }>();

   // On election pages the config comes from the route; elsewhere (e.g. the home
   // page) fall back to the only election when there is exactly one.
   const { data: routeElectionConfig } = useQuery({
      ...electionConfigQuery(electionConfigSlug),
      enabled: Boolean(electionConfigSlug),
      throwOnError: false,
   });
   const { data: electionConfigs } = useElectionConfigs();
   const electionConfig = routeElectionConfig ?? (electionConfigs?.length === 1 ? electionConfigs[0] : undefined);

   const label = electionConfig?.label;
   const countingInfoUrl = electionConfig?.counting_info_url;
   const votingUrl = electionConfig?.voting_url;

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
                           // biome-ignore lint/suspicious/noArrayIndexKey: order is fixed
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
                     <h4>
                        <Trans>Zie je een fout op de pagina?</Trans>
                     </h4>
                     <a href={REPORT_ERROR_URL} target="_blank" rel="noopener noreferrer">
                        <FontAwesomeIcon icon={faChevronRight} />
                        <Trans>Melding maken</Trans>
                     </a>
                  </div>
                  <div className="footer-col">
                     {label && <h4>{label}</h4>}
                     {countingInfoUrl && (
                        <a href={countingInfoUrl} target="_blank" rel="noopener noreferrer">
                           <ExternalLinkIcon />
                           <Trans>Uitleg over telproces</Trans>
                        </a>
                     )}
                     {votingUrl && (
                        <a href={votingUrl} target="_blank" rel="noopener noreferrer">
                           <ExternalLinkIcon />
                           <Trans>Stemmen</Trans>
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
                     <Trans>Verkiezingen waar de samenleving op kan vertrouwen</Trans>
                  </p>
                  <p className="footer-collab">
                     <Trans>In samenwerking met de Kiesraad</Trans>
                  </p>
               </div>
               <span className="footer-copy">© {currentYear} De Kiesraad</span>
            </div>
         </div>

         <LanguageSwitcher />
      </footer>
   );
}
