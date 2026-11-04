import { type Dispatch, type SetStateAction, useCallback, useMemo, useSyncExternalStore } from "react";
import { readCookie, writeCookie } from "@/utils/cookies.ts";

// Cookies have no change event, so writes through this hook notify its readers themselves.
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
   listeners.add(listener);
   return () => listeners.delete(listener);
}

function parseStored<T>(stored: string | null, defaultValue: T, isValid?: (value: unknown) => value is T): T {
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
 *
 * A stored value that is missing, unparsable or rejected by `isValid` falls back to `defaultValue`.
 * Rendering without a browser, and hydrating that markup, uses the default; other renders read the
 * cookie straight away. The cookie is only written once a value is set, and where cookies are
 * blocked a set value is lost. `defaultValue` and `isValid` must not change between renders.
 */
export function usePersistedState<T>(
   key: string,
   defaultValue: T,
   isValid?: (value: unknown) => value is T,
): [T, Dispatch<SetStateAction<T>>] {
   // The raw string is the snapshot: it compares equal between reads, where a parsed object would not.
   const stored = useSyncExternalStore(
      subscribe,
      () => readCookie(key),
      () => null,
   );

   // biome-ignore lint/correctness/useExhaustiveDependencies: the default and validator are fixed per call site
   const value = useMemo(() => parseStored(stored, defaultValue, isValid), [stored]);

   // biome-ignore lint/correctness/useExhaustiveDependencies: the default and validator are fixed per call site
   const setValue = useCallback(
      (action: SetStateAction<T>) => {
         const next = action instanceof Function ? action(parseStored(readCookie(key), defaultValue, isValid)) : action;
         writeCookie(key, JSON.stringify(next));
         for (const listener of listeners) listener();
      },
      [key],
   );

   return [value, setValue];
}
