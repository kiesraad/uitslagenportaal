import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api/client.ts";

// Lives outside main.tsx because the route config in router.tsx is built at module
// scope and has to close over this client to hand it to the loaders.
export const queryClient = new QueryClient({
   defaultOptions: {
      queries: {
         retry: (failureCount, error) => {
            if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
               return false;
            }
            return failureCount < 3;
         },
         staleTime: 60 * 1000, // 60s
      },
   },
});
