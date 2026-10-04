/**
 * The Aurora add-on's acceptance tests: a real sign-in, through a real Dex.
 *
 * They need the backend, Dex and Aurora running; `make acceptance-test` in
 * `frontend/aurora` lists how to start each.
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: './results',
  // One site, one Dex user: the tests sign the same person in and out.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  timeout: 30_000,
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
