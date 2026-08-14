import { defineConfig, devices } from '@playwright/test'

// Assumes the full stack is already running via docker compose on port 8080.
// See the root README for: docker compose up -d, migrate, reset_and_import.
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:8080'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? 'github' : 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
