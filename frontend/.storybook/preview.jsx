import '@plone/volto/config'; // This is the bootstrap for the global config - client side
import React from 'react';
import { StaticRouter } from 'react-router-dom';
import { IntlProvider } from 'react-intl';
import enMessages from '@root/../locales/en.json';

import '@root/theme';

import { withPage } from '@plone-collective/volto-identity/storybook/withPage';

export const parameters = {
  controls: {
    matchers: {
      color: /(background|color)$/i,
      date: /Date$/,
    },
  },
};

// Storybook applies these outermost-last, so `withPage` wraps the rest --
// which is the order Volto's own `start-client.jsx` has: the cookie provider
// is outside the router and the intl provider, not inside them.
export const decorators = [
  (Story) => (
    <IntlProvider messages={enMessages} locale="en" defaultLocale="en">
      <StaticRouter location="/">
        <Story />
      </StaticRouter>
    </IntlProvider>
  ),
  withPage,
];
