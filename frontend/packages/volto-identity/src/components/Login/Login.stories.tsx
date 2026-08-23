import type { Meta, StoryObj } from '@storybook/react';

import Login from './Login';
import {
  FAILED,
  LOADED,
  LOADING,
  PROVIDERS,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof Login> = {
  title: 'Identity/Login/Login',
  component: Login,
};
export default meta;

type Story = StoryObj<typeof Login>;

/** The whole page: the panel, the providers, and the password fallback. */
export const Default: Story = {
  decorators: [
    withStore({
      loginProviders: { ...LOADED, data: PROVIDERS },
      providerLogin: {},
      magicLinkSend: {},
      userSession: { token: null, login: {} },
    }),
  ],
};

export const Loading: Story = {
  decorators: [
    withStore({
      loginProviders: { ...LOADING, data: [] },
      providerLogin: {},
      magicLinkSend: {},
      userSession: { token: null, login: {} },
    }),
  ],
};

export const NoProvidersConfigured: Story = {
  decorators: [
    withStore({
      loginProviders: { ...LOADED, data: [] },
      providerLogin: {},
      magicLinkSend: {},
      userSession: { token: null, login: {} },
    }),
  ],
};

export const PasswordRefused: Story = {
  decorators: [
    withStore({
      loginProviders: { ...LOADED, data: PROVIDERS },
      providerLogin: {},
      magicLinkSend: {},
      userSession: { token: null, login: { error: FAILED.error } },
    }),
  ],
};
