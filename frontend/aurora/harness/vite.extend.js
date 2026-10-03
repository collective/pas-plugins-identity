/**
 * Adapt Vite to this repository's layout. Dev-only; never published.
 *
 * `identity-core` lives in `../packages`, outside this harness, and the Volto
 * harness installs it too. pnpm links a package's dependencies into its own
 * `node_modules`, so whichever harness installed last decides which React
 * `identity-core/node_modules/react` points at -- the Volto harness's
 * React 18, after a Volto install. Deduplicating its peers makes every import
 * of them resolve to Aurora's own copy instead, so the page carries one React.
 *
 * Vite also refuses to serve files outside the harness unless told to.
 */
import fs from 'node:fs';
import path from 'node:path';

const sharedPackages = path.resolve(import.meta.dirname, '..', '..', 'packages');
const corePackageJson = JSON.parse(
  fs.readFileSync(
    path.join(sharedPackages, 'identity-core', 'package.json'),
    'utf-8',
  ),
);
const peers = Object.keys(corePackageJson.peerDependencies ?? {});

export default function extendViteConfig(config) {
  return {
    ...config,
    resolve: {
      ...config.resolve,
      dedupe: [...new Set([...(config.resolve?.dedupe ?? []), ...peers])],
    },
    server: {
      ...config.server,
      fs: {
        ...config.server?.fs,
        allow: [...(config.server?.fs?.allow ?? []), sharedPackages],
      },
    },
  };
}
