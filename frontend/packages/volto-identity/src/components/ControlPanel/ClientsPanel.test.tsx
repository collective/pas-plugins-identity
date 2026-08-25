import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '../../testing';
import React from 'react';

import ClientsPanel from './ClientsPanel';
import type { OAuthClient, SigningKeyRing } from '../../types';

const CLIENT: OAuthClient = {
  '@id': '/@identity-clients/app',
  client_id: 'app',
  title: 'Example App',
  redirect_uris: ['https://app.example.org/cb'],
  grant_types: ['authorization_code'],
  scope: 'openid profile',
  auth_method: 'client_secret_post',
  public: false,
  enabled: true,
  service_user: '',
};

const PUBLIC_CLIENT: OAuthClient = {
  ...CLIENT,
  '@id': '/@identity-clients/spa',
  client_id: 'spa',
  title: 'Single Page App',
  auth_method: 'none',
  public: true,
};

const KEYS: SigningKeyRing = {
  '@id': '/@identity-keys',
  algorithm: 'RS256',
  ring_size: 3,
  jwks_uri: 'https://id.example.org/@@oauth-jwks',
  items_total: 2,
  items: [
    { kid: 'newest-kid', active: true },
    { kid: 'older-kid', active: false },
  ],
};

/**
 * The `add` and `edit` views are not rendered here: they are Volto's `Form`,
 * which needs a store and a router this renderer does not provide. What they
 * put on the wire is `helpers/clientSchema`'s own test, and how they look is
 * the stories'.
 */
function renderPanel(
  props: Partial<React.ComponentProps<typeof ClientsPanel>> = {},
) {
  const handlers = {
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
    onEdit: vi.fn(),
    onRotateSecret: vi.fn(),
    onDelete: vi.fn(),
    onRotateKey: vi.fn(),
    onDismissSecret: vi.fn(),
  };
  render(
    <ClientsPanel
      clients={[CLIENT]}
      keys={KEYS}
      loading={false}
      busy={false}
      minted={null}
      view="list"
      editing={null}
      formRef={React.createRef()}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

/** Accept the delete confirmation without a real dialog. */
function confirming(answer: boolean) {
  return vi.spyOn(window, 'confirm').mockReturnValue(answer);
}

describe('ClientsPanel', () => {
  it('lists the registered clients', () => {
    renderPanel();

    expect(screen.getByText('Example App')).toBeTruthy();
    expect(screen.getByText('app')).toBeTruthy();
  });

  it('says nothing is registered when nothing is', () => {
    renderPanel({ clients: [] });

    expect(screen.getByText(/No clients are registered/)).toBeTruthy();
  });

  it('shows a loading state', () => {
    renderPanel({ loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading clients');
  });

  it('distinguishes a public client from a confidential one', () => {
    renderPanel({ clients: [CLIENT, PUBLIC_CLIENT] });

    expect(screen.getByText(/Public \(PKCE required\)/)).toBeTruthy();
    expect(screen.getByText('Confidential')).toBeTruthy();
  });

  it('shows what a client may do, not only what it is called', () => {
    renderPanel();

    expect(screen.getByText('authorization_code')).toBeTruthy();
    expect(screen.getByText('openid profile')).toBeTruthy();
  });

  it('opens the edit form for a client', () => {
    const { onEdit } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));

    expect(onEdit).toHaveBeenCalledWith('app');
  });

  it('offers no secret rotation for a public client', () => {
    renderPanel({ clients: [PUBLIC_CLIENT] });

    expect(screen.queryByRole('button', { name: 'Rotate secret' })).toBeNull();
  });

  it('rotates a confidential client secret', () => {
    const { onRotateSecret } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Rotate secret' }));

    expect(onRotateSecret).toHaveBeenCalledWith('app');
  });

  it('warns that disabling also refuses existing tokens', () => {
    renderPanel({ clients: [{ ...CLIENT, enabled: false }] });

    expect(screen.getByText(/existing access tokens are refused/)).toBeTruthy();
  });

  it('unregisters a client once it is confirmed', () => {
    const confirm = confirming(true);
    const { onDelete } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Unregister' }));

    expect(onDelete).toHaveBeenCalledWith('app');
    confirm.mockRestore();
  });

  it('unregisters nothing when the confirmation is declined', () => {
    const confirm = confirming(false);
    const { onDelete } = renderPanel();

    fireEvent.click(screen.getByRole('button', { name: 'Unregister' }));

    expect(onDelete).not.toHaveBeenCalled();
    confirm.mockRestore();
  });

  it('shows a freshly minted secret over the listing', () => {
    renderPanel({ minted: { ...CLIENT, secret: 's3cr3t' } });

    expect(screen.getByRole('alertdialog')).toBeTruthy();
    expect(screen.getByDisplayValue('s3cr3t')).toBeTruthy();
  });

  it('shows no secret when none was minted', () => {
    renderPanel();

    expect(screen.queryByRole('alertdialog')).toBeNull();
  });

  it('disables every action while a request is in flight', () => {
    renderPanel({ busy: true });

    expect(
      (screen.getByRole('button', { name: 'Unregister' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it('keeps the key ring out of the listing', () => {
    renderPanel();

    expect(screen.queryByText('newest-kid')).toBeNull();
  });

  it('describes the signing ring without any key material', () => {
    renderPanel({ view: 'keys' });

    expect(screen.getByText('newest-kid')).toBeTruthy();
    expect(screen.getByText(/2 of 3 in the ring/)).toBeTruthy();
  });

  it('says which key is signing', () => {
    renderPanel({ view: 'keys' });

    expect(screen.getByText(/— signing/)).toBeTruthy();
    expect(screen.getByText(/verifying only/)).toBeTruthy();
  });

  it('warns what rotating past the ring bound costs', () => {
    renderPanel({ view: 'keys' });

    expect(
      screen.getByText(/invalidate tokens\s+still in flight/),
    ).toBeTruthy();
  });

  it('rotates the signing key', () => {
    const { onRotateKey } = renderPanel({ view: 'keys' });

    fireEvent.click(screen.getByText('Rotate signing key'));

    expect(onRotateKey).toHaveBeenCalled();
  });

  it('does not render the key section before it has loaded', () => {
    renderPanel({ view: 'keys', keys: null });

    expect(screen.getByText(/Loading keys/)).toBeTruthy();
  });

  it('does not offer a rotation while one is in flight', () => {
    renderPanel({ view: 'keys', busy: true });

    expect(
      (screen.getByText('Rotate signing key') as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
