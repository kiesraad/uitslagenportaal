import { type DehydratedState, dehydrate, QueryClient } from "@tanstack/react-query";
import { data } from "react-router";
import { ApiError, isNotFoundError } from "./api/client.ts";

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

export type ServerLoaderData = { dehydratedState: DehydratedState };

/** A query cache for one server request. A failing backend gets the error page rather than a page that waits through retries. */
export function createServerQueryClient() {
   const client = createQueryClient();
   client.setDefaultOptions({ queries: { ...client.getDefaultOptions().queries, retry: false } });
   return client;
}

/**
 * A route `loader` that runs a page's load function on the server, in a query cache of its own for
 * this request, and hands the result to the page dehydrated. A 404 from the API becomes a 404 page.
 */
export function serverLoader<Args>(load: (client: QueryClient, args: Args) => Promise<unknown>) {
   return async (args: Args): Promise<ServerLoaderData> => {
      const client = createServerQueryClient();
      try {
         await load(client, args);
      } catch (error) {
         if (isNotFoundError(error)) throw data(null, { status: 404 });
         throw error;
      }
      return { dehydratedState: dehydrate(client) };
   };
}
