const API_ORIGIN = import.meta.env.VITE_API_BASE_URL;

export class ApiError extends Error {
   readonly status: number;

   constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
   }
}

/** A 404 means the election, region or stembureau asked for does not exist. */
export function isNotFoundError(error: unknown): boolean {
   return error instanceof ApiError && error.status === 404;
}

export async function apiGet<T>(path: string): Promise<T> {
   const response = await fetch(`${API_ORIGIN}${path}`);

   if (!response.ok) {
      throw new ApiError(`Request failed: ${response.statusText}`, response.status);
   }

   return response.json() as Promise<T>;
}
