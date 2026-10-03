/**
 * Resolve `identity-core`'s peers to Volto's own copies.
 *
 * `identity-core` lives in `frontend/packages`, where the Volto harness and
 * the Aurora harness (`frontend/aurora`) both install it. pnpm links a
 * package's dependencies into its own `node_modules`, so whichever harness
 * installed last decides which React `identity-core/node_modules/react`
 * points at. After an Aurora install that is React 19, and webpack, resolving
 * from the file's real path, bundles it beside Volto's React 18: two Reacts
 * on one page, and the first hook call fails.
 *
 * Aliasing the peers to the copies Volto itself resolves gives the page one
 * of each. In a project that installs the published packages there is one
 * copy to begin with, and this changes nothing. A peer Volto already aliases
 * -- `@plone/components` -- is left to Volto.
 */
const fs = require('fs');
const path = require('path');

const corePackageJson = JSON.parse(
  fs.readFileSync(
    require.resolve('@plone-collective/identity-core/package.json'),
    'utf-8',
  ),
);
const peers = Object.keys(corePackageJson.peerDependencies ?? {});
const voltoPath = path.dirname(require.resolve('@plone/volto/package.json'));

const plugins = (defaultPlugins) => defaultPlugins;

const modify = (config) => {
  const alias = { ...config.resolve.alias };
  for (const peer of peers) {
    if (peer in alias) {
      continue;
    }
    alias[peer] = path.dirname(
      require.resolve(`${peer}/package.json`, { paths: [voltoPath] }),
    );
  }
  config.resolve.alias = alias;
  return config;
};

module.exports = { plugins, modify };
