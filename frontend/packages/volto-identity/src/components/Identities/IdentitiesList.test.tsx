import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import IdentitiesList from './IdentitiesList';
import type { Identity, LoginProvider, ProfileEmail } from '../../types';

const DEX: Identity = {
  '@id': '/@identities/dex/subject-1',
  provider: 'dex',
  subject: 'subject-1',
  title: 'Dex',
  created: '2026-08-21T10:00:00+00:00',
  last_login: null,
  can_unlink: true,
};

const GITHUB: LoginProvider = {
  '@id': '/@login-providers/github',
  id: 'github',
  title: 'GitHub',
  driver: 'github',
};

const ADDRESS: ProfileEmail = {
  address: 'erico@plone.org',
  verified: false,
  preferred: true,
};

function renderList(
  props: Partial<React.ComponentProps<typeof IdentitiesList>> = {},
) {
  const onLink = vi.fn();
  const onVerifyEmail = vi.fn();
  const onUnlink = vi.fn();
  render(
    <IdentitiesList
      identities={[DEX]}
      available={[GITHUB]}
      emails={[ADDRESS]}
      loading={false}
      busy={false}
      emailSent={false}
      onLink={onLink}
      onVerifyEmail={onVerifyEmail}
      onUnlink={onUnlink}
      {...props}
    />,
  );
  return { onLink, onVerifyEmail, onUnlink };
}

describe('IdentitiesList', () => {
  it('lists what the user owns', () => {
    renderList();

    expect(screen.getByText('Dex')).toBeTruthy();
    expect(screen.getByText('subject-1')).toBeTruthy();
  });

  it('offers what they can still add', () => {
    renderList();

    expect(screen.getByText('GitHub')).toBeTruthy();
  });

  it('reports the provider to link', () => {
    const { onLink } = renderList();

    fireEvent.click(screen.getByText('GitHub'));

    expect(onLink).toHaveBeenCalledWith(GITHUB);
  });

  it('reports the identity to remove', () => {
    const { onUnlink } = renderList();

    fireEvent.click(screen.getByText('Remove'));

    expect(onUnlink).toHaveBeenCalledWith(DEX);
  });

  it('refuses to offer removing the last way in', () => {
    // Surfaced. A button that only fails when pressed is worse than one
    // that explains itself.
    renderList({ identities: [{ ...DEX, can_unlink: false }] });

    const button = screen.getByText('Remove') as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(button.title).toContain('only way to sign in');
  });

  it('disables everything while something is in flight', () => {
    renderList({ busy: true });

    for (const button of screen.getAllByRole('button')) {
      expect((button as HTMLButtonElement).disabled).toBe(true);
    }
  });

  it('says so while loading', () => {
    renderList({ loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading');
  });

  it('says so when nothing is linked', () => {
    renderList({ identities: [] });

    expect(screen.getByText(/no external sign-in methods/i)).toBeTruthy();
  });

  it('offers no add section when there is nothing to add', () => {
    renderList({ available: [] });

    expect(screen.queryByText('Add another')).toBeNull();
  });

  it('reports a failure', () => {
    renderList({ error: { status: 409 } });

    expect(screen.getByRole('alert')).toBeTruthy();
  });
});

describe('IdentitiesList and your own addresses', () => {
  it('lists the addresses on the profile', () => {
    // Not a box to type one into. The address a magic link proves is
    // whatever was typed, so a free-text field here verified any mailbox at
    // all -- and a verified address is what a new provider account can be
    // auto-attached to.
    renderList();

    expect(screen.queryByLabelText('Email address')).toBeNull();
    expect(screen.getByText('erico@plone.org')).toBeTruthy();
  });

  it('offers to verify one that is not verified yet', () => {
    const { onVerifyEmail } = renderList();

    fireEvent.click(screen.getByRole('button', { name: 'Verify' }));

    expect(onVerifyEmail).toHaveBeenCalledWith('erico@plone.org');
  });

  it('says so rather than offering to verify a verified one', () => {
    renderList({ emails: [{ ...ADDRESS, verified: true }] });

    expect(screen.queryByRole('button', { name: 'Verify' })).toBeNull();
    expect(screen.getByText('Verified')).toBeTruthy();
  });

  it('marks the address the site uses', () => {
    renderList();

    expect(screen.getByText('Preferred')).toBeTruthy();
  });

  it('says the mail is out once it is', () => {
    renderList({ emailSent: true });

    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('points at the profile when there is nothing to verify', () => {
    renderList({ emails: [], profileUrl: '/identity-profiles/erico' });

    expect(screen.getByText(/carries no email address/i)).toBeTruthy();
    expect(screen.getByText('Edit your profile')).toBeTruthy();
  });
});
