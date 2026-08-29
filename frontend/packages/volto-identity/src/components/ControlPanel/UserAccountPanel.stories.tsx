import type { Meta, StoryObj } from '@storybook/react';

import UserAccountPanel from './UserAccountPanel';
import type { UserAccount } from '../../types';

const ACCOUNT: UserAccount = {
  '@id': '/@user-account/erico',
  userid: 'erico',
  fullname: 'Érico Andrei',
  profile_url: '/identity-profiles/erico',
  identities: [
    {
      provider: 'github',
      title: 'GitHub',
      subject: '99',
      created: '2026-03-02T11:40:00+00:00',
      last_login: '2026-08-21T18:03:00+00:00',
      provider_configured: true,
      provider_enabled: true,
      groups: ['site-editors'],
    },
    {
      provider: 'email',
      title: 'Email',
      subject: 'erico@plone.org',
      created: '2026-01-14T09:12:00+00:00',
      last_login: null,
      provider_configured: true,
      provider_enabled: true,
      groups: [],
    },
  ],
  emails: [
    { address: 'erico@plone.org', verified: true, preferred: true },
    { address: 'erico@example.com', verified: false, preferred: false },
  ],
  last_authenticated: '2026-08-21T18:03:00+00:00',
  events_total: 2,
  events: [
    {
      event: 'authenticated',
      provider: 'github',
      success: true,
      timestamp: '2026-08-21T18:03:00+00:00',
      detail: {},
    },
    {
      event: 'magic-link-sent',
      provider: 'email',
      success: true,
      timestamp: '2026-08-20T09:00:00+00:00',
      detail: {},
    },
  ],
};

const meta: Meta<typeof UserAccountPanel> = {
  title: 'Identity/ControlPanel/UserAccountPanel',
  component: UserAccountPanel,
  args: { account: ACCOUNT, loading: false },
};
export default meta;

type Story = StoryObj<typeof UserAccountPanel>;

/** An account with two providers and a verified address. */
export const Linked: Story = {};

/** A password account: nothing linked, and nothing wrong with that. */
export const PasswordOnly: Story = {
  args: {
    account: { ...ACCOUNT, identities: [], events: [], events_total: 0 },
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
      ...ACCOUNT,
      identities: [{ ...ACCOUNT.identities[0], provider_enabled: false }],
    },
  },
};

/** A provider deleted out from under a stored identity. */
export const RemovedProvider: Story = {
  args: {
    account: {
      ...ACCOUNT,
      identities: [
        {
          ...ACCOUNT.identities[0],
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
      ...ACCOUNT,
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
