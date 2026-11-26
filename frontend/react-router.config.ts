import type { Config } from "@react-router/dev/config";

export default {
   appDirectory: "src",
   // Served by Node. Pages still load their data in the browser, so the server renders the shell.
   ssr: true,
   // In @react-router/dev 8.5.1 the splitter drops exported function declarations a clientLoader
   // calls (the pages' `loadX`), leaving "loadX is not defined" at runtime; re-check on upgrade.
   splitRouteModules: false,
} satisfies Config;
