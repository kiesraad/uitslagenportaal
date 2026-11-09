import { StrictMode } from "react";
import { hydrateRoot } from "react-dom/client";
import { HydratedRouter } from "react-router/dom";
import { detectLocale, loadCatalog, resolveLocale } from "./i18n";

// The shell in index.html was prerendered in the language of `<html lang>`; its catalogue has to be
// active before hydrating, or the markup would not match. The visitor's catalogue loads alongside,
// unawaited, so the root clientLoader finds it loaded; a failure there surfaces in that loader.
loadCatalog(detectLocale()).catch(() => {});
await loadCatalog(resolveLocale(document.documentElement.lang));

hydrateRoot(
   document,
   <StrictMode>
      <HydratedRouter />
   </StrictMode>,
);
