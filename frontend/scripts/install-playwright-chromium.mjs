import { spawnSync } from "node:child_process";

// Frontend Docker image only runs Vite; skip the ~150MB browser download there.
// CI installs the browser itself with `npx playwright install --only-shell chromium`
// (no --with-deps: ubuntu-latest already ships every lib Chromium needs).
if (process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD === "1") {
   process.exit(0);
}

const result = spawnSync("playwright", ["install", "chromium"], {
   stdio: "inherit",
   shell: true,
});

process.exit(result.status ?? 1);
