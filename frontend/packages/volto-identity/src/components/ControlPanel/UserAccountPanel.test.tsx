import { describe, expect, it } from 'vitest';
import { render, screen } from '../../testing';
import React from 'react';

import UserAccountPanel, { formatDate } from './UserAccountPanel';
import type { UserAccount } from '../../types';

const ACCOUNT: UserAccount = {
  '@id': '/@user-account/alice',
  userid: 'alice',
  fullname: 'Alice Liddell',
  profile_url: '/identity-profiles/alice',
  identities: [
    {
      provider: 'github',
      title: 'GitHub',
      subject: '99',
      created: '2026-03-02T11:40:00+00:00',
      last_login: '2026-08-21T18:03:00+00:00',
      provider_configured: true,
      provider_enabled: true,
      groups: [],
    },
  ],
  emails: [{ address: 'alice@example.com', verified: true, preferred: true }],
  last_authenticated: '2026-08-21T18:03:00+00:00',
  events_total: 1,
  events: [
    {
      event: 'authenticated',
      provider: 'github',
      success: true,
      timestamp: '2026-08-21T18:03:00+00:00',
      detail: {},
    },
  ],
};

function renderPanel(
  props: Partial<React.ComponentProps<typeof UserAccountPanel>> = {},
) {
  render(<UserAccountPanel account={ACCOUNT} loading={false} {...props} />);
}

describe('formatDate', () => {
  it('answers nothing for a missing timestamp', () => {
    expect(formatDate(null)).toBeNull();
  });

  it('answers nothing rather than "Invalid Date"', () => {
    // A backend that changed shape should not print that into a control
    // panel.
    expect(formatDate('not a date')).toBeNull();
  });
});

describe('UserAccountPanel', () => {
  it('names the providers rather than their ids', () => {
    // The first of the two questions. `@users` carries bare ids, which is not
    // something to show somebody.
    renderPanel();

    expect(screen.getByText('GitHub')).toBeTruthy();
  });

  it('says when they last signed in', () => {
    // The second. Nothing in Plone records it.
    renderPanel();

    expect(screen.getByText(/Last signed in/)).toBeTruthy();
  });

  it('does not claim they never signed in when the log is simply empty', () => {
    // The log is bounded, so a dormant account has had its entries dropped.
    renderPanel({ account: { ...ACCOUNT, last_authenticated: null } });

    expect(screen.getByText('Not in the retained log')).toBeTruthy();
  });

  it('flags an identity whose provider is switched off', () => {
    // It looks like a broken login and reads like nothing.
    renderPanel({
      account: {
        ...ACCOUNT,
        identities: [{ ...ACCOUNT.identities[0], provider_enabled: false }],
      },
    });

    expect(screen.getByText('Disabled')).toBeTruthy();
  });

  it('flags an identity whose provider was removed', () => {
    renderPanel({
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
    });

    expect(screen.getByText('Not configured')).toBeTruthy();
    expect(screen.queryByText('Disabled')).toBeNull();
  });

  it('says so for a password-only account', () => {
    renderPanel({ account: { ...ACCOUNT, identities: [] } });

    expect(screen.getByText(/password only/)).toBeTruthy();
  });

  it('shows which addresses are verified', () => {
    renderPanel();

    expect(screen.getByText('alice@example.com')).toBeTruthy();
    expect(screen.getByText('Verified')).toBeTruthy();
  });

  it('lists the recent events', () => {
    renderPanel();

    expect(screen.getByText('authenticated')).toBeTruthy();
  });

  it('says so while loading', () => {
    renderPanel({ loading: true, account: null });

    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('says so when the read was refused', () => {
    renderPanel({ account: null, error: { status: 403 } });

    expect(screen.getByRole('alert')).toBeTruthy();
  });
});
