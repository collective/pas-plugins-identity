/**
 * Refuse to run unless the harness installs React Aria twice.
 *
 * A project's install decides how many copies of `react-aria-components` it
 * has, and this add-on cannot choose for it: the one it publishes resolves
 * its own range, and Volto's `@plone/components` resolves Volto's. When the
 * two land on different versions, a react-aria widget built from both
 * copies loses its context and the page fails to render (#153).
 *
 * So `packages/volto-identity` pins a `react-aria-components` that differs
 * from Volto's catalogue, and these tests run against that split. Once
 * Volto's catalogue reaches the same version, the copies would merge and
 * every test here would pass whether or not the add-on handles a split.
 * This check stops that from happening silently.
 */
import path from 'node:path';

// Playwright loads this file as CommonJS: `frontend/package.json` declares
// no module type.
const frontend = path.resolve(__dirname, '..');

/**
 * The `react-aria-components` that a package resolves.
 *
 * @param from The directory to resolve from.
 * @returns Where the copy lives, and its version.
 */
function reactAriaFrom(from: string): { root: string; version: string } {
  const manifest = require.resolve('react-aria-components/package.json', {
    paths: [from],
  });
  return { root: path.dirname(manifest), version: require(manifest).version };
}

export default function globalSetup(): void {
  const addon = path.join(frontend, 'packages', 'volto-identity');
  const components = path.dirname(
    require.resolve('@plone/components/package.json', { paths: [addon] }),
  );
  const ours = reactAriaFrom(addon);
  const theirs = reactAriaFrom(components);
  if (ours.root === theirs.root) {
    throw new Error(
      `The add-on and @plone/components share react-aria-components ` +
        `${ours.version}. These tests need two copies: pin a different ` +
        `version in packages/volto-identity/package.json.`,
    );
  }
}
