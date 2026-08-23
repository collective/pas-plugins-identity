import type { Meta, StoryObj } from '@storybook/react';

import ProvidersControlPanel from './ProvidersControlPanel';
import {
  CONFIGURED,
  DRIVERS,
  LOADED,
  LOADING,
  USER_FIELDS_STATE,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ProvidersControlPanel> = {
  title: 'Identity/ControlPanel/ProvidersControlPanel',
  component: ProvidersControlPanel,
};
export default meta;

type Story = StoryObj<typeof ProvidersControlPanel>;

/** The site-wide settings, as `@controlpanels/identity-providers` serves them. */
const SETTINGS = {
  '@id': 'http://localhost:8080/Plone/@controlpanels/identity-providers',
  schema: {
    title: 'Identity providers',
    fieldsets: [{ id: 'default', title: 'Default', fields: ['callback_url'] }],
    properties: {
      callback_url: {
        title: 'Login callback URL',
        description:
          'Absolute URL of the frontend route the provider redirects to.',
        type: 'string',
      },
    },
    required: [],
  },
  data: { callback_url: 'https://example.org/login-identity' },
};

const base = {
  configuredProviders: { ...LOADED, data: CONFIGURED },
  identityDrivers: { ...LOADED, data: DRIVERS },
  providerCreate: {},
  providerUpdate: {},
  providerDelete: {},
  providerTest: {},
  vocabularies: USER_FIELDS_STATE,
  controlpanels: { controlpanel: SETTINGS },
};

export const Default: Story = { decorators: [withStore(base)] };

export const Loading: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADING, data: [] } }),
  ],
};

/** A fresh site: the Add action lives in the toolbar, not in the page. */
export const Empty: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADED, data: [] } }),
  ],
};

/** Nothing to configure with, because no add-on registered a driver. */
export const NoDrivers: Story = {
  decorators: [
    withStore({
      ...base,
      configuredProviders: { ...LOADED, data: [] },
      identityDrivers: { ...LOADED, data: [] },
    }),
  ],
};

/** The state that makes every sign-in fail at the last step. */
export const NoCallbackUrl: Story = {
  decorators: [
    withStore({
      ...base,
      controlpanels: {
        controlpanel: { ...SETTINGS, data: { callback_url: '' } },
      },
    }),
  ],
};
