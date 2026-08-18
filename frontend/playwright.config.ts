import { defineConfig, devices } from '@playwright/test'

// Isolated throwaway stack on :8081 (docker-compose.e2e.yml).
// for testing purposes
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:8081'

export default defineConfig({
  testDir: './playwright',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'bash ../.docker/e2e/start.sh',
    url: baseURL,
    timeout: 5 * 60 * 1000,  // 5 minutes
    reuseExistingServer: false,
    stdout: 'pipe',
    stderr: 'pipe',
    gracefulShutdown: { signal: 'SIGTERM', timeout: 30_000 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
