import { StrictMode } from "react";
import { hydrateRoot } from "react-dom/client";
import { HydratedRouter } from "react-router/dom";
import { loadCatalog, resolveLocale } from "./i18n";

// The shell in index.html was prerendered in the language of `<html lang>`; its catalogue has to be
// active before hydrating, or the markup would not match. The root clientLoader then loads the visitor's.
await loadCatalog(resolveLocale(document.documentElement.lang));

hydrateRoot(
   document,
   <StrictMode>
      <HydratedRouter />
   </StrictMode>,
);
