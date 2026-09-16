/// <reference types="vite/client" />

interface ImportMetaEnv {
   readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
   readonly env: ImportMetaEnv;
}

// `@lingui/vite-plugin` compiles `.po` catalogues into message modules on import.
declare module "*.po" {
   import type { Messages } from "@lingui/core";
   export const messages: Messages;
}
