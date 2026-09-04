import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '../../testing';
import React from 'react';

import SecretReveal from './SecretReveal';
import type { OAuthClient } from '../../types';

const CLIENT: OAuthClient = {
  '@id': '/@identity-clients/app',
  client_id: 'app',
  title: 'Example App',
  redirect_uris: [],
  grant_types: ['authorization_code'],
  scope: [],
  auth_method: 'client_secret_post',
  public: false,
  enabled: true,
  service_user: '',
  secret: 's3cr3t',
  notice: 'This is the only time this secret is shown.',
};

function renderReveal(client: OAuthClient = CLIENT) {
  const onDismiss = vi.fn();
  render(<SecretReveal client={client} onDismiss={onDismiss} />);
  return onDismiss;
}

describe('SecretReveal', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('shows the secret', () => {
    renderReveal();

    expect(screen.getByDisplayValue('s3cr3t')).toBeTruthy();
  });

  it('carries the server’s own notice', () => {
    renderReveal();

    expect(screen.getByText(/only time this secret is shown/)).toBeTruthy();
  });

  it('says so even when the server sent no notice', () => {
    renderReveal({ ...CLIENT, notice: undefined });

    expect(screen.getByText(/only time this secret is shown/)).toBeTruthy();
  });

  it('announces itself, because dismissing it loses the secret', () => {
    renderReveal();

    expect(screen.getByRole('alertdialog')).toBeTruthy();
  });

  it('copies to the clipboard', async () => {
    renderReveal();

    fireEvent.click(screen.getByText('Copy'));

    await waitFor(() =>
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('s3cr3t'),
    );
    await waitFor(() => expect(screen.getByText('Copied')).toBeTruthy());
  });

  it('stays usable when the browser refuses clipboard access', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    });
    renderReveal();

    fireEvent.click(screen.getByText('Copy'));

    // Still readable and selectable, which is the fallback that matters.
    await waitFor(() => expect(screen.getByText('Copy')).toBeTruthy());
    expect(screen.getByDisplayValue('s3cr3t')).toBeTruthy();
  });

  it('selects the whole secret on focus', () => {
    renderReveal();
    const field = screen.getByDisplayValue('s3cr3t') as HTMLInputElement;
    field.select = vi.fn();

    fireEvent.focus(field);

    expect(field.select).toHaveBeenCalled();
  });

  it('is dismissed only when the operator says they have saved it', () => {
    const onDismiss = renderReveal();

    fireEvent.click(screen.getByText('I have saved it'));

    expect(onDismiss).toHaveBeenCalled();
  });
});
