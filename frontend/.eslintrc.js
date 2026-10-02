const fs = require('fs');
const projectRootPath = __dirname;
const { AddonRegistry } = require('@plone/registry/addon-registry');

let coreLocation;
if (fs.existsSync(`${projectRootPath}/core`))
  coreLocation = `${projectRootPath}/core`;
else if (fs.existsSync(`${projectRootPath}/../../core`))
  coreLocation = `${projectRootPath}/../../core`;

const { registry } = AddonRegistry.init(`${coreLocation}/packages/volto`);

// Extends ESlint configuration for adding the aliases to `src` directories in Volto addons
const addonAliases = Object.keys(registry.packages).map((o) => [
  o,
  registry.packages[o].modulePath,
]);

module.exports = {
  extends: `${coreLocation}/packages/volto/.eslintrc`,
  rules: {
    'import/no-unresolved': 1,
  },
  overrides: [
    {
      // identity-core is shared by the Volto and the Aurora add-on, so it may
      // import neither frontend, nor anything only one of them provides.
      files: ['packages/identity-core/**'],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: [
              {
                group: [
                  '@plone/volto',
                  '@plone/volto/*',
                  '@plone/volto-*',
                  '@plone/aurora',
                  '@plone/aurora/*',
                  '@plone/react-router',
                  '@plone/registry',
                  '@plone/registry/*',
                  '@plone-collective/volto-identity',
                  '@plone-collective/volto-identity/*',
                  '@plone-collective/aurora-identity',
                  '@plone-collective/aurora-identity/*',
                  '**/volto-identity/**',
                  '**/aurora-identity/**',
                  'react',
                  'react/*',
                  'react-dom',
                  'react-dom/*',
                  'react-redux',
                  'react-intl',
                  'react-i18next',
                  'i18next',
                  'react-router',
                  'react-router-dom',
                  'semantic-ui-react',
                ],
                message:
                  'identity-core is framework-agnostic: adapt it in volto-identity or aurora-identity instead.',
              },
            ],
          },
        ],
      },
    },
  ],
  settings: {
    'import/resolver': {
      alias: {
        map: [
          ['@plone/volto', `${coreLocation}/packages/volto/src`],
          ['@plone/volto-slate', `${coreLocation}/packages/volto-slate/src`],
          ['@plone/registry', `${coreLocation}/packages/registry/src`],
          [
            '@plone-collective/volto-identity',
            './packages/volto-identity/src',
          ],
          ...addonAliases,
        ],
        extensions: ['.js', '.jsx', '.ts', '.tsx', '.json'],
      },
    },
  },
};
