import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'jsdom',
    // Testing Library unmounts after each test only when it can find a global
    // `afterEach`; without it, one test's DOM leaks into the next.
    globals: true,
    include: ['**/*.test.{ts,tsx}'],
    exclude: ['node_modules/**'],
  },
  resolve: {
    // identity-core is shared with the Volto harness, and pnpm may have
    // linked its React to that harness's copy; see ../../aurora/harness.
    dedupe: ['react', 'react-dom', 'react-aria-components'],
  },
});
