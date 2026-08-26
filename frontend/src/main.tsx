import { I18nProvider } from "@lingui/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import "./index.css";
import { detectLocale, i18n, loadCatalog } from "./i18n";
import { queryClient } from "./queryClient.ts";
import { router } from "./router.tsx";

const rootElem = document.getElementById("root");

if (rootElem === null) {
   throw new Error("No root element found");
}

// Awaited before the first render so the app never flashes untranslated message
// ids, and so no Suspense boundary is needed for the catalogue.
await loadCatalog(detectLocale());

createRoot(rootElem).render(
   <StrictMode>
      <I18nProvider i18n={i18n}>
         <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
         </QueryClientProvider>
      </I18nProvider>
   </StrictMode>,
);
