/**
 * Build this add-on with the React Aria that `@plone/components` uses.
 *
 * The add-on composes react-aria widgets from two places: some pieces from
 * `react-aria-components` itself (`Table`, `TableBody`, `Tab`, `FileTrigger`,
 * `useDragAndDrop`), others from `@plone/components` (`Row`, `Column`,
 * `Tabs`, `Button`), which wrap react-aria in their turn. The pieces talk
 * through React contexts, and a context belongs to one copy of the library.
 * When a project's install gives the two packages different copies, a `Row`
 * finds no table around it and the page fails to render (#153).
 *
 * How many copies a project has is its install's decision, not this
 * package's. So the client build resolves every `react-aria-components`
 * import in this package *as if `@plone/components` had made it*: the same
 * resolver, the same conditions, and therefore the same file and the same
 * module instance.
 *
 * The server build needs nothing. Volto's server bundle leaves
 * `react-aria-components` external, so every import of it, ours and
 * `@plone/components`', is one `require` at runtime.
 */
const fs = require('fs');
const path = require('path');

const REQUEST = 'react-aria-components';

/**
 * The directory `@plone/components` resolves its own imports from.
 *
 * @returns {string} The real path of the package this add-on was installed
 *   beside.
 */
function ploneComponentsDirectory() {
  const manifest = require.resolve('@plone/components/package.json', {
    paths: [__dirname],
  });
  return fs.realpathSync(path.dirname(manifest));
}

/**
 * Resolve one bare request from another package's directory.
 *
 * Re-enters webpack's resolver with the request's directory swapped, so the
 * result is exactly what the other package would get.
 */
class ResolveFromPlugin {
  /**
   * @param {string} request The bare module request to redirect.
   * @param {string} directory The directory to resolve it from.
   */
  constructor(request, directory) {
    this.request = request;
    this.directory = directory;
  }

  apply(resolver) {
    const target = resolver.ensureHook('resolve');
    resolver
      .getHook('described-resolve')
      .tapAsync('ResolveFromPlugin', (request, resolveContext, callback) => {
        if (
          request.request !== this.request ||
          request.path === this.directory
        ) {
          callback();
          return;
        }
        resolver.doResolve(
          target,
          { ...request, path: this.directory },
          `${this.request} as ${this.directory} resolves it`,
          resolveContext,
          callback,
        );
      });
  }
}

const plugins = (defaultPlugins) => defaultPlugins;

const modify = (config, { target }) => {
  if (target !== 'web') {
    return config;
  }
  const source = path.join(__dirname, 'src');
  config.module.rules.push({
    // Modules this package's own files import. Both spellings of the
    // directory: webpack reports real paths, and a project may reach this
    // package through a symbolic link.
    include: [...new Set([source, fs.realpathSync(source)])],
    resolve: {
      plugins: [new ResolveFromPlugin(REQUEST, ploneComponentsDirectory())],
    },
  });
  return config;
};

module.exports = {
  plugins,
  modify,
  ploneComponentsDirectory,
};
