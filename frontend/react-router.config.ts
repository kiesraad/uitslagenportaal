import type { Config } from "@react-router/dev/config";

export default {
   appDirectory: "src",
   // A static single-page app: the build prerenders only the shell into build/client/index.html.
   ssr: false,
   // In @react-router/dev 8.5.1 the splitter drops exported function declarations a clientLoader
   // calls (the pages' `loadX`), leaving "loadX is not defined" at runtime; re-check on upgrade.
   splitRouteModules: false,
} satisfies Config;
