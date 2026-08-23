import type { Meta, StoryObj } from '@storybook/react';

import Identities from './Identities';
import {
  IDENTITIES,
  LOADED,
  LOADING,
  PROVIDERS,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof Identities> = {
  title: 'Identity/Identities/Identities',
  component: Identities,
};
export default meta;

type Story = StoryObj<typeof Identities>;

const base = {
  identities: { ...LOADED, data: IDENTITIES },
  loginProviders: { ...LOADED, data: PROVIDERS },
  identityLinking: {},
  identityUnlink: {},
};

/** Where a signed-in user manages their own ways in. */
export const Default: Story = { decorators: [withStore(base)] };

export const Loading: Story = {
  decorators: [withStore({ ...base, identities: { ...LOADING, data: [] } })],
};

export const Unlinking: Story = {
  decorators: [withStore({ ...base, identityUnlink: LOADING })],
};
