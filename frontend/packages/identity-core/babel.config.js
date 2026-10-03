// Used by `pnpm i18n` alone, to extract this package's messages; the
// frontends transpile the source with their own configuration. Extraction is
// the Volto harness's job: `pnpm i18n` runs Volto's own `i18n.cjs` from
// `frontend/core`, and the Volto harness's `.npmrc` hoists the preset and the
// plugin this names to `frontend/node_modules`. This package depends on none
// of them, because the Aurora harness has none of them.
//
// Messages are declared with `defineMessages` from `#i18n`, not from
// `react-intl`, which this package may not import. `moduleSourceName` tells
// the extractor which import to look for.
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['@plone/razzle'],
    plugins: [
      [
        'react-intl',
        {
          messagesDir: './build/messages/',
          moduleSourceName: '#i18n',
        },
      ],
    ],
  };
};
