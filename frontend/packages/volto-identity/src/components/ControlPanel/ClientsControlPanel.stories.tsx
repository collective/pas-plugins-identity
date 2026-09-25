import type { Meta, StoryObj } from '@storybook/react';

import ClientsControlPanel from './ClientsControlPanel';
import {
  CLIENTS,
  KEYRING,
  LOADED,
  LOADING,
  SERVER_SETTINGS,
  UNCONFIGURED_SERVER_SETTINGS,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ClientsControlPanel> = {
  title: 'Identity/ControlPanel/ClientsControlPanel',
  component: ClientsControlPanel,
};
export default meta;

type Story = StoryObj<typeof ClientsControlPanel>;

const base = {
  oauthClients: { ...LOADED, data: CLIENTS },
  signingKeys: { ...LOADED, data: KEYRING },
  clientCreate: {},
  clientUpdate: {},
  clientDelete: {},
  clientSecretRotate: {},
  keyRotate: {},
  controlpanels: {
    controlpanel: SERVER_SETTINGS,
    get: LOADED,
    update: {},
  },
};

export const Default: Story = { decorators: [withStore(base)] };

export const Loading: Story = {
  decorators: [withStore({ ...base, oauthClients: { ...LOADING, data: [] } })],
};

export const RotatingAKey: Story = {
  decorators: [withStore({ ...base, keyRotate: LOADING })],
};

/** Straight after deploying: no issuer yet, and the page says so. */
export const NotConfigured: Story = {
  decorators: [
    withStore({
      ...base,
      controlpanels: {
        ...base.controlpanels,
        controlpanel: UNCONFIGURED_SERVER_SETTINGS,
      },
    }),
  ],
};
