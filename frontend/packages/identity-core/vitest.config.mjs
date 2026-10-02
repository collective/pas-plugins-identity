import { defineConfig } from 'vitest/config';

// Plain vitest, on purpose: nothing in this package may need Volto or Aurora
// to run, and its tests are where that shows first.
export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
  },
});
