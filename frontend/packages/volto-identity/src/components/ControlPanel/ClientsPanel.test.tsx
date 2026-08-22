import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
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

function renderPanel(
  props: Partial<React.ComponentProps<typeof ClientsPanel>> = {},
) {
  const handlers = {
    onCreate: vi.fn(),
    onToggle: vi.fn(),
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
      {...handlers}
      {...props}
    />,
  );
  return handlers;
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

  it('offers no secret rotation for a public client', () => {
    renderPanel({ clients: [PUBLIC_CLIENT] });

    expect(screen.queryByText('Rotate secret')).toBeNull();
  });

  it('rotates a confidential client secret', () => {
    const { onRotateSecret } = renderPanel();

    fireEvent.click(screen.getByText('Rotate secret'));

    expect(onRotateSecret).toHaveBeenCalledWith('app');
  });

  it('disables an enabled client', () => {
    const { onToggle } = renderPanel();

    fireEvent.click(screen.getByText('Disable'));

    expect(onToggle).toHaveBeenCalledWith('app', false);
  });

  it('enables a disabled one', () => {
    const { onToggle } = renderPanel({
      clients: [{ ...CLIENT, enabled: false }],
    });

    fireEvent.click(screen.getByText('Enable'));

    expect(onToggle).toHaveBeenCalledWith('app', true);
  });

  it('warns that disabling also refuses existing tokens', () => {
    renderPanel({ clients: [{ ...CLIENT, enabled: false }] });

    expect(screen.getByText(/existing access tokens are refused/)).toBeTruthy();
  });

  it('unregisters a client', () => {
    const { onDelete } = renderPanel();

    fireEvent.click(screen.getByText('Unregister'));

    expect(onDelete).toHaveBeenCalledWith('app');
  });

  it('registers a client, splitting redirect URIs by line', () => {
    const { onCreate } = renderPanel();

    fireEvent.change(screen.getByLabelText(/Client ID/), {
      target: { value: 'new-app' },
    });
    fireEvent.change(screen.getByLabelText(/Redirect URIs/), {
      target: {
        value: 'https://a.example.org/cb\n\n https://b.example.org/cb ',
      },
    });
    fireEvent.click(screen.getByText('Register'));

    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        client_id: 'new-app',
        redirect_uris: ['https://a.example.org/cb', 'https://b.example.org/cb'],
      }),
    );
  });

  it('registers a public client when asked', () => {
    const { onCreate } = renderPanel();

    fireEvent.change(screen.getByLabelText(/Client ID/), {
      target: { value: 'spa' },
    });
    fireEvent.click(screen.getByLabelText(/Public client/));
    fireEvent.click(screen.getByText('Register'));

    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ public: true }),
    );
  });

  it('describes the signing ring without any key material', () => {
    renderPanel();

    expect(screen.getByText('newest-kid')).toBeTruthy();
    expect(screen.getByText(/2 of 3 in the ring/)).toBeTruthy();
  });

  it('says which key is signing', () => {
    renderPanel();

    expect(screen.getByText(/— signing/)).toBeTruthy();
    expect(screen.getByText(/verifying only/)).toBeTruthy();
  });

  it('warns what rotating past the ring bound costs', () => {
    renderPanel();

    expect(
      screen.getByText(/invalidate tokens\s+still in flight/),
    ).toBeTruthy();
  });

  it('rotates the signing key', () => {
    const { onRotateKey } = renderPanel();

    fireEvent.click(screen.getByText('Rotate signing key'));

    expect(onRotateKey).toHaveBeenCalled();
  });

  it('does not render the key section before it has loaded', () => {
    renderPanel({ keys: null });

    expect(screen.getByText(/Loading keys/)).toBeTruthy();
  });

  it('shows a freshly minted secret', () => {
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

    expect((screen.getByText('Unregister') as HTMLButtonElement).disabled).toBe(
      true,
    );
    expect(
      (screen.getByText('Rotate signing key') as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
