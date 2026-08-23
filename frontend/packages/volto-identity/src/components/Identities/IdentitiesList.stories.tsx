import type { Meta, StoryObj } from '@storybook/react';

import IdentitiesList from './IdentitiesList';
import {
  FAILED,
  IDENTITIES,
  ONLY_IDENTITY,
  PROVIDERS,
} from '../../stories/fixtures';

const meta: Meta<typeof IdentitiesList> = {
  title: 'Identity/Identities/IdentitiesList',
  component: IdentitiesList,
  args: {
    identities: IDENTITIES,
    available: PROVIDERS,
    loading: false,
    busy: false,
    onLink: () => {},
    onUnlink: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof IdentitiesList>;

export const Several: Story = {};

/**
 * The last way in cannot be unlinked: doing so would lock the user out of an
 * account they have no password for.
 */
export const LastRemaining: Story = { args: { identities: ONLY_IDENTITY } };

/** One that has never been used since it was linked. */
export const NeverUsed: Story = {
  args: { identities: [{ ...IDENTITIES[0], last_login: null }] },
};

export const Empty: Story = { args: { identities: [] } };

export const Loading: Story = { args: { loading: true, identities: [] } };

/** While a link or unlink is in flight, nothing else may be started. */
export const Busy: Story = { args: { busy: true } };

export const Failed: Story = { args: { error: FAILED.error } };

/** Every provider already linked, so there is nothing left to add. */
export const NothingLeftToLink: Story = { args: { available: [] } };
