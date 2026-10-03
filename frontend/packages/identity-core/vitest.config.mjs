import { defineConfig } from 'vitest/config';

// Plain vitest, on purpose: nothing in this package may need Volto or Aurora
// to run, and its tests are where that shows first.
export default defineConfig({
  test: {
    environment: 'jsdom',
    // Testing Library unmounts after each test only when it can find a global
    // `afterEach`; without it, one test's DOM leaks into the next.
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
