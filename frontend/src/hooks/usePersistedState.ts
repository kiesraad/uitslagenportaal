import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { readCookie, writeCookie } from "@/utils/cookies.ts";

function readStored<T>(key: string, defaultValue: T, isValid?: (value: unknown) => value is T): T {
   const stored = readCookie(key);
   if (stored === null) return defaultValue;
   try {
      const parsed: unknown = JSON.parse(stored);
      return !isValid || isValid(parsed) ? (parsed as T) : defaultValue;
   } catch {
      return defaultValue;
   }
}

/**
 * `useState` whose value is kept in a cookie named `key`, so it survives navigation and reloads.
 * A missing, unparsable or (per `isValid`) invalid stored value falls back to `defaultValue`. The stored
 * value is applied after mount, so the first render matches markup rendered without a browser.
 */
export function usePersistedState<T>(
   key: string,
   defaultValue: T,
   isValid?: (value: unknown) => value is T,
): [T, Dispatch<SetStateAction<T>>] {
   const [value, setValue] = useState<T>(defaultValue);
   const [loaded, setLoaded] = useState(false);

   // biome-ignore lint/correctness/useExhaustiveDependencies: reads once per key; the default and validator are fixed per call site
   useEffect(() => {
      setValue(readStored(key, defaultValue, isValid));
      setLoaded(true);
   }, [key]);

   useEffect(() => {
      // Before the read, `value` is still the default and would overwrite what is stored.
      if (loaded) writeCookie(key, JSON.stringify(value));
   }, [key, value, loaded]);

   return [value, setValue];
}
