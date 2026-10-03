// Used by `pnpm i18n` alone, to extract this package's messages; the
// frontends transpile the source with their own configuration.
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
