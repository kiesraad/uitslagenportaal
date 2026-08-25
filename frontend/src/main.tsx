import { I18nProvider } from "@lingui/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { ApiError } from "./api/client.ts";
import { detectLocale, i18n, loadCatalog } from "./i18n";

const queryClient = new QueryClient({
   defaultOptions: {
      queries: {
         retry: (failureCount, error) => {
            if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
               return false;
            }
            return failureCount < 3;
         },
         staleTime: 5 * 60 * 1000, // 5min
      },
   },
});
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
            <App />
         </QueryClientProvider>
      </I18nProvider>
   </StrictMode>,
);
