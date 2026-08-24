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

function renderList(
  props: Partial<React.ComponentProps<typeof IdentitiesList>> = {},
) {
  const onLink = vi.fn();
  const onUnlink = vi.fn();
  render(
    <IdentitiesList
      identities={[DEX]}
      available={[GITHUB]}
      loading={false}
      busy={false}
      onLink={onLink}
      onUnlink={onUnlink}
      {...props}
    />,
  );
  return { onLink, onUnlink };
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
