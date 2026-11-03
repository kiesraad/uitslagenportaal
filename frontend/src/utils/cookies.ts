const ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60;

/** A cookie's value from a `Cookie` header, or from the page's own cookies when none is given. */
export function readCookie(name: string, cookieHeader?: string | null): string | null {
   let cookies: string;
   try {
      cookies = cookieHeader ?? document.cookie;
   } catch {
      // Sandboxed iframes throw on any cookie access.
      return null;
   }

   const entry = cookies.split(";").find((part) => part.trim().startsWith(`${name}=`));
   if (entry === undefined) return null;
   try {
      return decodeURIComponent(entry.trim().slice(name.length + 1));
   } catch {
      return null;
   }
}

/** Stores a value in a site-wide cookie for a year, so a server render can read it too. */
export function writeCookie(name: string, value: string): void {
   try {
      // biome-ignore lint/suspicious/noDocumentCookie: the Cookie Store API is async and not widely supported
      document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${ONE_YEAR_IN_SECONDS}; SameSite=Lax`;
   } catch {
      // Sandboxed iframes throw on any cookie access; the value is simply not stored.
   }
}
