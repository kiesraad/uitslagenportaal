import { isRouteErrorResponse } from "react-router";

// Empty when the API is served from the same origin
export const API_ORIGIN = import.meta.env.VITE_API_BASE_URL ?? "";

// A server render has no page origin to call relative to, so it calls the backend directly.
const FETCH_ORIGIN = import.meta.env.SSR ? (process.env.SSR_API_ORIGIN ?? "") : API_ORIGIN;
const SERVER_FETCH_TIMEOUT_MS = 10_000;

export class ApiError extends Error {
   readonly status: number;

   constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
   }
}

export function isNotFoundError(error: unknown): boolean {
   return (error instanceof ApiError || isRouteErrorResponse(error)) && error.status === 404;
}

export async function apiGet<T>(path: string): Promise<T> {
   const response = await fetch(
      `${FETCH_ORIGIN}${path}`,
      import.meta.env.SSR ? { signal: AbortSignal.timeout(SERVER_FETCH_TIMEOUT_MS) } : undefined,
   );

   if (!response.ok) {
      throw new ApiError(`Request failed: ${response.statusText}`, response.status);
   }

   return response.json() as Promise<T>;
}
