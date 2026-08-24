import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import { ApiError } from "./api/client.ts";
import App from "./App.tsx";

const queryClient = new QueryClient({
   defaultOptions: {
      queries: {
         retry: (failureCount, error) => {
            if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
               return false;
            }
            return failureCount < 3;
         },
      },
   },
});
const rootElem = document.getElementById("root");

if (rootElem === null) {
   throw new Error("No root element found");
}

createRoot(rootElem).render(
   <StrictMode>
      <QueryClientProvider client={queryClient}>
         <App />
      </QueryClientProvider>
   </StrictMode>,
);
