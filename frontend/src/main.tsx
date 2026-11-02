import { config as fontAwesomeConfig } from "@fortawesome/fontawesome-svg-core";
import "@fortawesome/fontawesome-svg-core/styles.css";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import "./index.css";
import { detectLocale, loadCatalog } from "./i18n";
import { queryClient } from "./queryClient.ts";
import { router } from "./router.tsx";

// The icon styles ship with the page's CSS; injected at runtime, server-rendered icons show unstyled until then.
fontAwesomeConfig.autoAddCss = false;

const rootElem = document.getElementById("root");

if (rootElem === null) {
   throw new Error("No root element found");
}

// Awaited before the first render so the app never flashes untranslated message
// ids, and so no Suspense boundary is needed for the catalogue.
await loadCatalog(detectLocale());

createRoot(rootElem).render(
   <StrictMode>
      <QueryClientProvider client={queryClient}>
         <RouterProvider router={router} />
      </QueryClientProvider>
   </StrictMode>,
);
