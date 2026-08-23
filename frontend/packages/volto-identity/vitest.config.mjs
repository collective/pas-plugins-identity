import { defineConfig } from 'vitest/config';
import voltoVitestConfig from '@plone/volto/vitest.config.mjs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const COMPONENTS_SRC = path.resolve(
  __dirname,
  '../../core/packages/components/src',
);

/**
 * Volto's shared aliases map `@plone/components` onto that package's `src`,
 * so an import written the way a real build needs it --
 * `@plone/components/src/styles/basic/Foo.css`, which is how volto-authomatic
 * imports widget stylesheets -- would resolve to `src/src/...` here and fail.
 *
 * This maps the full subpath, and does it *before* spreading Volto's aliases
 * so the longer, more specific key is matched first.
 */
const withComponentsSrc = (project) => ({
  ...project,
  resolve: {
    ...project.resolve,
    alias: {
      '@plone/components/src': COMPONENTS_SRC,
      ...(project.resolve?.alias ?? {}),
    },
  },
});

export default defineConfig({
  ...voltoVitestConfig,
  resolve: {
    ...voltoVitestConfig.resolve,
    alias: {
      '@plone/components/src': COMPONENTS_SRC,
      ...(voltoVitestConfig.resolve?.alias ?? {}),
      '@plone/volto': path.resolve(__dirname, '../../core/packages/volto/src'),
    },
  },
  test: {
    ...voltoVitestConfig.test,
    projects: (voltoVitestConfig.test?.projects ?? []).map(withComponentsSrc),
  },
});
