import { defineConfig } from 'vitest/config';
import voltoVitestConfig from '@plone/volto/vitest.config.mjs';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const COMPONENTS_SRC = path.resolve(
  __dirname,
  '../../core/packages/components/src',
);

/**
 * Volto aliases every add-on's name to its `src`, so a deep import of
 * `identity-core` is written relative to `src` -- which is what webpack
 * resolves. Vitest resolves through `node_modules` instead, where the same
 * path is one `src/` short; this puts it back. The package itself is left
 * alone: only a path below it is rewritten.
 */
const IDENTITY_CORE_SUBPATHS = {
  find: /^@plone-collective\/identity-core\/(.+)$/,
  replacement: path.resolve(__dirname, '../identity-core/src/$1'),
};

/**
 * `identity-core`'s peer dependencies, resolved to this harness's copies.
 *
 * The test counterpart of `razzle.extend.js`. Both harnesses install
 * `identity-core`, so its `node_modules` points at whichever installed last;
 * after an Aurora install that is React 19's React Aria, and a core
 * component rendered here would run on a second React. Deduplicating makes
 * Vite resolve each of these from this package instead.
 */
const CORE_PEERS = Object.keys(
  JSON.parse(
    fs.readFileSync(
      path.resolve(__dirname, '../identity-core/package.json'),
      'utf-8',
    ),
  ).peerDependencies ?? {},
);

/**
 * Turn aliases into Vite's array form, which is the only one a regular
 * expression can be written in. Vite converts an object to the same array,
 * in the same order, so matching is unchanged.
 *
 * @param alias Aliases, as an object or an array.
 * @returns The same aliases, as an array.
 */
const asArray = (alias = {}) =>
  Array.isArray(alias)
    ? alias
    : Object.entries(alias).map(([find, replacement]) => ({
        find,
        replacement,
      }));

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
    dedupe: [...new Set([...(project.resolve?.dedupe ?? []), ...CORE_PEERS])],
    alias: [
      IDENTITY_CORE_SUBPATHS,
      ...asArray({ '@plone/components/src': COMPONENTS_SRC }),
      ...asArray(project.resolve?.alias),
    ],
  },
});

export default defineConfig({
  ...voltoVitestConfig,
  resolve: {
    ...voltoVitestConfig.resolve,
    alias: [
      IDENTITY_CORE_SUBPATHS,
      ...asArray({
        '@plone/components/src': COMPONENTS_SRC,
        ...(voltoVitestConfig.resolve?.alias ?? {}),
        '@plone/volto': path.resolve(
          __dirname,
          '../../core/packages/volto/src',
        ),
      }),
    ],
  },
  test: {
    ...voltoVitestConfig.test,
    projects: (voltoVitestConfig.test?.projects ?? []).map(withComponentsSrc),
  },
});
