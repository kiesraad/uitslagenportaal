import { useSyncExternalStore } from "react";

const TICK_MS = 60_000;

let now: Date | null = null;
let intervalId: ReturnType<typeof setInterval> | undefined;
const listeners = new Set<() => void>();

function tick() {
   now = new Date();
   for (const listener of listeners) listener();
}

// One clock for all readers, running while any is mounted.
function subscribe(listener: () => void): () => void {
   if (listeners.size === 0) {
      now = new Date();
      intervalId = setInterval(tick, TICK_MS);
   }
   listeners.add(listener);
   return () => {
      listeners.delete(listener);
      if (listeners.size === 0) clearInterval(intervalId);
   };
}

function getSnapshot(): Date {
   now ??= new Date();
   return now;
}

/**
 * The current time, updated every minute; `null` on the server and while hydrating. The server's
 * clock and time zone are not the visitor's, and cached HTML can be old, so output that depends on
 * the time is left to the browser.
 */
export function useNow(): Date | null {
   return useSyncExternalStore(subscribe, getSnapshot, () => null);
}
