import { defineConfig } from 'vitest/config';
import voltoVitestConfig from '@plone/volto/vitest.config.mjs';
import { createRequire } from 'module';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { ploneComponentsDirectory } = require('./razzle.extend.js');

const COMPONENTS_SRC = path.resolve(
  __dirname,
  '../../core/packages/components/src',
);

/**
 * The test runner's half of `razzle.extend.js`: resolve this package's
 * `react-aria-components` imports as `@plone/components` resolves its own.
 *
 * The development harness installs two copies on purpose (see
 * `acceptance/global-setup.ts`), so without this the tests would mix them
 * exactly as #153 did.
 */
const COMPONENTS_DIRECTORY = ploneComponentsDirectory();
const reactAriaOfPloneComponents = {
  name: 'react-aria-of-plone-components',
  enforce: 'pre',
  async resolveId(source, importer) {
    if (
      source !== 'react-aria-components' ||
      !importer ||
      importer.startsWith(COMPONENTS_DIRECTORY)
    ) {
      return null;
    }
    return this.resolve(
      source,
      path.join(COMPONENTS_DIRECTORY, 'package.json'),
      { skipSelf: true },
    );
  },
};

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
  plugins: [reactAriaOfPloneComponents, ...(project.plugins ?? [])],
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
  plugins: [reactAriaOfPloneComponents, ...(voltoVitestConfig.plugins ?? [])],
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
