import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import ApplicationsPanel from './ApplicationsPanel';
import type { OAuthGrants } from '../../types';

const GRANTS: OAuthGrants = {
  '@id': 'http://id.example.org/@oauth-grants',
  access_token_ttl: 900,
  items: [
    {
      '@id': 'http://id.example.org/@oauth-grants/app',
      client_id: 'app',
      title: 'Example App',
      registered: true,
      enabled: true,
      granted_at: '2026-08-01T10:00:00+00:00',
      scopes: [
        { id: 'openid', claims: [] },
        { id: 'profile', claims: ['name', 'preferred_username'] },
        { id: 'email', claims: ['email', 'email_verified'] },
      ],
    },
  ],
};

function renderPanel(
  props: Partial<React.ComponentProps<typeof ApplicationsPanel>> = {},
) {
  const onWithdraw = vi.fn();
  const onSelect = vi.fn();
  render(
    <ApplicationsPanel
      grants={GRANTS}
      loading={false}
      selected={null}
      withdrawing={null}
      onSelect={onSelect}
      onWithdraw={onWithdraw}
      {...props}
    />,
  );
  return { onWithdraw, onSelect };
}

/** The listing with one grant replaced. */
function withGrant(changes: Partial<OAuthGrants['items'][0]>): OAuthGrants {
  return { ...GRANTS, items: [{ ...GRANTS.items[0], ...changes }] };
}

describe('ApplicationsPanel', () => {
  it('names each application the way the person saw it', () => {
    renderPanel();

    expect(screen.getByText('Example App')).toBeTruthy();
  });

  it('says when they authorized it', () => {
    renderPanel();

    expect(screen.getByText(/August/)).toBeTruthy();
  });

  it('counts what each one reads rather than listing it', () => {
    // Four rows of claim lists is a wall nobody reads; the names are one
    // click away, on the view for deciding rather than the one for
    // scanning.
    renderPanel();

    expect(screen.getByText('4 fields')).toBeTruthy();
    expect(screen.queryByText('preferred_username')).toBeNull();
  });

  it('says an application reads nothing rather than showing a zero', () => {
    renderPanel({
      grants: withGrant({ scopes: [{ id: 'openid', claims: [] }] }),
    });

    expect(screen.getByText('Nothing')).toBeTruthy();
  });

  it('opens one application on its own', () => {
    const { onSelect } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Details' }));

    expect(onSelect).toHaveBeenCalledWith('app');
  });

  it('says what withdrawing cannot reach', () => {
    // An access token already minted is self-encoded with no denylist. A
    // screen promising an instant cutoff would be promising something the
    // server cannot do.
    renderPanel();

    expect(screen.getByText(/up to 15 minutes/)).toBeTruthy();
  });

  it('rounds that window up rather than down', () => {
    // Saying "1 minute" for 90 seconds would understate it.
    renderPanel({ grants: { ...GRANTS, access_token_ttl: 90 } });

    expect(screen.getByText(/up to 2 minutes/)).toBeTruthy();
  });

  it('offers to withdraw from the listing', () => {
    // Without opening the details first: somebody who recognises the name
    // has already decided.
    const { onWithdraw } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Withdraw access' }));

    expect(onWithdraw).toHaveBeenCalledWith('app');
  });

  it('takes no second answer while one is on its way', () => {
    renderPanel({ withdrawing: 'app' });

    expect(
      (
        screen.getByRole('button', {
          name: 'Withdraw access',
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });

  it('still offers to withdraw an application that is gone', () => {
    // The agreement outlives the registration, so the record has to be
    // removable or it is one the user can see and not act on.
    renderPanel({ grants: withGrant({ registered: false, enabled: false }) });

    expect(screen.getByText(/no longer registered/)).toBeTruthy();
    expect(
      screen.getByRole('button', { name: 'Withdraw access' }),
    ).toBeTruthy();
  });

  it('says what withdrawing cannot reach on the listing too', () => {
    // The caveat belongs wherever the button is.
    renderPanel();

    expect(screen.getByText(/up to 15 minutes/)).toBeTruthy();
  });

  it('says when an application is already being refused', () => {
    renderPanel({ grants: withGrant({ enabled: false }) });

    expect(screen.getByText(/disabled and is being refused/)).toBeTruthy();
  });

  it('says nothing is authorized rather than showing an empty page', () => {
    // Which is an answer somebody opened this page to get.
    renderPanel({ grants: { ...GRANTS, items: [] } });

    expect(
      screen.getByText(/have not authorized any application/),
    ).toBeTruthy();
  });

  it('shows one application in full when it is opened', () => {
    renderPanel({ selected: 'app' });

    expect(screen.getByText('preferred_username')).toBeTruthy();
    expect(screen.getByText(/You authorized this application on/)).toBeTruthy();
  });

  it('names each claim once however many scopes carry it', () => {
    renderPanel({
      selected: 'app',
      grants: withGrant({
        scopes: [
          { id: 'profile', claims: ['name'] },
          { id: 'other', claims: ['name'] },
        ],
      }),
    });

    expect(screen.getAllByText('name')).toHaveLength(1);
  });

  it('says plainly when an application reads nothing', () => {
    // An empty list under "It can read:" reads as a rendering failure.
    renderPanel({
      selected: 'app',
      grants: withGrant({ scopes: [{ id: 'openid', claims: [] }] }),
    });

    expect(screen.getByText(/Nothing beyond the fact/)).toBeTruthy();
  });

  it('shows the scopes as well, where the decision is made', () => {
    renderPanel({ selected: 'app' });

    expect(screen.getByText('openid profile email')).toBeTruthy();
  });

  it('offers the way back', () => {
    const { onSelect } = renderPanel({ selected: 'app' });

    fireEvent.click(screen.getByRole('button', { name: /Back to the list/ }));

    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it('falls back to the listing when the selection is gone', () => {
    // Which is what a withdrawal leaves behind for one render.
    renderPanel({ selected: 'vanished' });

    expect(screen.getByText('Example App')).toBeTruthy();
    expect(screen.queryByText('preferred_username')).toBeNull();
  });

  it('says so while the listing is loading', () => {
    renderPanel({ grants: null, loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading');
  });

  it('waits rather than reporting a failure before the answer arrives', () => {
    renderPanel({ grants: null, loading: false });

    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('reports a listing it could not read', () => {
    renderPanel({ grants: null, error: new Error('nope') });

    expect(screen.getByRole('alert')).toBeTruthy();
    expect(
      screen.queryByRole('button', { name: 'Withdraw access' }),
    ).toBeNull();
  });
});
