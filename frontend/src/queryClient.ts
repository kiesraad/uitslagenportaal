import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "./api/client.ts";

export function createQueryClient() {
   return new QueryClient({
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
}

// The browser's client, shared by the root layout's provider and the route modules' clientLoaders.
export const queryClient = createQueryClient();
