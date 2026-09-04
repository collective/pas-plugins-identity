import type { Meta, StoryObj } from '@storybook/react';

import UserAccountPanel from './UserAccountPanel';
import { USER_ACCOUNT } from '../../stories/fixtures';

const meta: Meta<typeof UserAccountPanel> = {
  title: 'Identity/ControlPanel/UserAccountPanel',
  component: UserAccountPanel,
  args: { account: USER_ACCOUNT, loading: false },
};
export default meta;

type Story = StoryObj<typeof UserAccountPanel>;

/** An account with two providers and a verified address. */
export const Linked: Story = {};

/** A password account: nothing linked, and nothing wrong with that. */
export const PasswordOnly: Story = {
  args: {
    account: { ...USER_ACCOUNT, identities: [], events: [], events_total: 0 },
  },
};

/**
 * An identity against a provider somebody turned off.
 *
 * This is what a "broken login" report actually looks like from here, and
 * without the badge it reads as nothing at all.
 */
export const DisabledProvider: Story = {
  args: {
    account: {
      ...USER_ACCOUNT,
      identities: [{ ...USER_ACCOUNT.identities[0], provider_enabled: false }],
    },
  },
};

/** A provider deleted out from under a stored identity. */
export const RemovedProvider: Story = {
  args: {
    account: {
      ...USER_ACCOUNT,
      identities: [
        {
          ...USER_ACCOUNT.identities[0],
          provider_configured: false,
          provider_enabled: false,
        },
      ],
    },
  },
};

/**
 * Nothing in the retained log.
 *
 * Not the same as never signing in: the log is bounded per user, so a dormant
 * account has had its entries dropped.
 */
export const Dormant: Story = {
  args: {
    account: {
      ...USER_ACCOUNT,
      last_authenticated: null,
      events: [],
      events_total: 0,
    },
  },
};

export const Loading: Story = { args: { account: null, loading: true } };

export const Refused: Story = {
  args: { account: null, loading: false, error: { status: 403 } },
};
