/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";
import { lingui, linguiTransformerBabelPreset } from "@lingui/vite-plugin";
import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Set when running behind the reverse proxy (see docker-compose.yml) so the
// HMR websocket reconnects through the proxy's published port rather than
// the container-internal dev-server port.
const hmrClientPort = process.env.VITE_HMR_CLIENT_PORT ? Number(process.env.VITE_HMR_CLIENT_PORT) : undefined;

// https://vite.dev/config/
export default defineConfig({
   plugins: [
      react(),
      // Makes `.po` catalogues importable as compiled message modules, so there
      // is no separate `lingui compile` step and no compiled artefacts to commit.
      lingui(),
      // The Lingui macros need a Babel pass.
      babel({ presets: [linguiTransformerBabelPreset()] }),
      tailwindcss(),
   ],
   resolve: {
      alias: {
         "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
   },
   server: {
      host: true,
      hmr: hmrClientPort ? { clientPort: hmrClientPort } : undefined,
      watch: {
         usePolling: true,
      },
   },
   test: {
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
   },
});
