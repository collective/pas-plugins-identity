import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import IdentitiesList from './IdentitiesList';
import type { Identity, LoginProvider } from '../../types';

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

const EMAIL: LoginProvider = {
  '@id': '/@login-providers/email',
  id: 'email',
  title: 'Email',
  driver: 'email',
};

function renderList(
  props: Partial<React.ComponentProps<typeof IdentitiesList>> = {},
) {
  const onLink = vi.fn();
  const onLinkEmail = vi.fn();
  const onUnlink = vi.fn();
  render(
    <IdentitiesList
      identities={[DEX]}
      available={[GITHUB]}
      loading={false}
      busy={false}
      emailSent={false}
      onLink={onLink}
      onLinkEmail={onLinkEmail}
      onUnlink={onUnlink}
      {...props}
    />,
  );
  return { onLink, onLinkEmail, onUnlink };
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

describe('IdentitiesList and the email provider', () => {
  it('offers an address field rather than a button', () => {
    // The defect: rendered as a button, clicking it posted a link request
    // for a provider that has no authorize URL to answer with.
    renderList({ available: [EMAIL] });

    expect(screen.queryByRole('button', { name: 'Email' })).toBeNull();
    expect(screen.getByLabelText('Email address')).toBeTruthy();
  });

  it('reports the address to link', () => {
    const { onLinkEmail } = renderList({ available: [EMAIL] });

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'erico@plone.org' },
    });
    fireEvent.click(screen.getByRole('button', { name: /confirmation/i }));

    expect(onLinkEmail).toHaveBeenCalledWith(EMAIL, 'erico@plone.org');
  });

  it('still renders redirect providers as buttons beside it', () => {
    renderList({ available: [GITHUB, EMAIL] });

    expect(screen.getByText('GitHub')).toBeTruthy();
    expect(screen.getByLabelText('Email address')).toBeTruthy();
  });

  it('says the mail is out once it is', () => {
    renderList({ available: [EMAIL], emailSent: true });

    expect(screen.queryByLabelText('Email address')).toBeNull();
    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('offers no address field when the site has no email provider', () => {
    renderList({ available: [GITHUB] });

    expect(screen.queryByLabelText('Email address')).toBeNull();
  });
});
