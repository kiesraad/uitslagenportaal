import { type Dispatch, type SetStateAction, useEffect, useState } from "react";

/**
 * `useState` whose value is kept in local storage under `key`, so it survives navigation and reloads.
 * A missing, unparsable or (per `isValid`) invalid stored value falls back to `defaultValue`.
 */
export function usePersistedState<T>(
   key: string,
   defaultValue: T,
   isValid?: (value: unknown) => value is T,
): [T, Dispatch<SetStateAction<T>>] {
   const [value, setValue] = useState<T>(() => {
      try {
         const stored = localStorage.getItem(key);
         if (stored === null) return defaultValue;
         const parsed: unknown = JSON.parse(stored);
         return !isValid || isValid(parsed) ? (parsed as T) : defaultValue;
      } catch {
         // Broken JSON, or a sandboxed iframe that throws on any localStorage access.
         return defaultValue;
      }
   });

   useEffect(() => {
      try {
         localStorage.setItem(key, JSON.stringify(value));
      } catch {
         // Sandboxed iframe: the value simply does not survive a reload.
      }
   }, [key, value]);

   return [value, setValue];
}
