import type { Meta, StoryObj } from '@storybook/react';

import ProvidersControlPanel from './ProvidersControlPanel';
import {
  CONFIGURED,
  DRIVERS,
  LOADED,
  LOADING,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ProvidersControlPanel> = {
  title: 'Identity/ControlPanel/ProvidersControlPanel',
  component: ProvidersControlPanel,
};
export default meta;

type Story = StoryObj<typeof ProvidersControlPanel>;

const base = {
  configuredProviders: { ...LOADED, data: CONFIGURED },
  identityDrivers: { ...LOADED, data: DRIVERS },
  providerCreate: {},
  providerUpdate: {},
  providerDelete: {},
  providerTest: {},
};

export const Default: Story = { decorators: [withStore(base)] };

export const Loading: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADING, data: [] } }),
  ],
};

export const Testing: Story = {
  decorators: [withStore({ ...base, providerTest: LOADING })],
};
