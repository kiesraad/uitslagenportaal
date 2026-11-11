/// <reference types="vitest/config" />
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { lingui, linguiTransformerBabelPreset } from "@lingui/vite-plugin";
import { reactRouter } from "@react-router/dev/vite";
import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, normalizePath } from "vite";
import { viteStaticCopy } from "vite-plugin-static-copy";

// Set when running behind the reverse proxy (see docker-compose.yml) so the
// HMR websocket reconnects through the proxy's published port rather than
// the container-internal dev-server port.
const hmrClientPort = process.env.VITE_HMR_CLIENT_PORT ? Number(process.env.VITE_HMR_CLIENT_PORT) : undefined;

// PDF.js decodes JBIG2 and JPEG 2000 images, common in scanned PVs, with these files.
const pdfjsWasmDir = normalizePath(
   path.join(path.dirname(createRequire(import.meta.url).resolve("pdfjs-dist/package.json")), "wasm"),
);

// https://vite.dev/config/
export default defineConfig({
   plugins: [
      // Vitest renders components without the framework build, so it keeps the plain React plugin.
      process.env.VITEST ? react() : reactRouter(),
      // Makes `.po` catalogues importable as compiled message modules, so there
      // is no separate `lingui compile` step and no compiled artefacts to commit.
      lingui(),
      // The Lingui macros need a Babel pass.
      babel({ presets: [linguiTransformerBabelPreset()] }),
      tailwindcss(),
      viteStaticCopy({
         targets: [{ src: pdfjsWasmDir, dest: "pdfjs-wasm", rename: { stripBase: true } }],
      }),
   ],
   resolve: {
      alias: {
         "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
   },
   build: {
      rolldownOptions: {
         output: {
            codeSplitting: {
               groups: [
                  {
                     name: "react",
                     test: /node_modules[/\\](react|react-dom|scheduler)[/\\]/,
                     priority: 40,
                  },
                  {
                     name: "react-router",
                     test: /node_modules[/\\]react-router[/\\]/,
                     priority: 30,
                  },
                  {
                     name: "react-query",
                     test: /node_modules[/\\]@tanstack[/\\]/,
                     priority: 30,
                  },
                  {
                     name: "markdown",
                     test: /node_modules[/\\]react-markdown[/\\]/,
                     priority: 20,
                  },
                  {
                     name: "fontawesome",
                     test: /node_modules[/\\]@fortawesome[/\\]/,
                     priority: 20,
                  },
                  {
                     name: "vendor",
                     // A group chunk loads on every page; PDF.js stays in the viewer's lazy chunk.
                     test: /node_modules[/\\](?!react-pdf[/\\]|pdfjs-dist[/\\])/,
                     priority: 10,
                  },
               ],
            },
         },
      },
   },
   server: {
      host: true,
      hmr: hmrClientPort ? { clientPort: hmrClientPort } : undefined,
      watch: {
         usePolling: true,
      },
   },
   preview: {
      // The built app calls the API on its own origin (VITE_API_BASE_URL is empty), so
      // whatever serves build/client/ has to forward /api to Django the way the nginx proxy
      // does in compose. Used by the Python browser suite in CI, which drives the
      // build rather than the dev server.
      proxy: {
         "/api": "http://127.0.0.1:8000",
      },
   },
   test: {
      environment: "jsdom",
      setupFiles: ["./tests/setup.ts"],
      include: ["tests/**/*.test.{ts,tsx}"],
   },
});
