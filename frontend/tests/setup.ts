import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
   cleanup();
   // jsdom keeps cookies for the whole file; a saved language or setting would leak into the next test.
   for (const entry of document.cookie.split(";")) {
      const name = entry.split("=")[0].trim();
      // biome-ignore lint/suspicious/noDocumentCookie: expiring a cookie in a test
      if (name) document.cookie = `${name}=; path=/; max-age=0`;
   }
});
