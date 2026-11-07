/**
 * The Volto add-on's acceptance tests, in a real browser against a real site.
 *
 * They need the backend's acceptance server and the Volto development
 * server running; see `make acceptance-test` in `frontend/`.
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: './results',
  globalSetup: './global-setup.ts',
  // One site: the tests add and remove its providers and users.
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // The first visit to a page compiles it in the development server.
  timeout: 60_000,
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
