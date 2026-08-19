import { spawnSync } from 'node:child_process'

// Frontend Docker image only runs Vite; skip the ~150MB browser download there.
// CI should run `npx playwright install --with-deps chromium` instead (OS libs).
if (process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD === '1') {
  process.exit(0)
}

const result = spawnSync('playwright', ['install', 'chromium'], {
  stdio: 'inherit',
  shell: true,
})

process.exit(result.status ?? 1)
