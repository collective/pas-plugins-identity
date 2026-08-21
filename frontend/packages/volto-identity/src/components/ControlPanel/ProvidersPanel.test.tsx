import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';

import ProvidersPanel from './ProvidersPanel';
import { SECRET_SENTINEL } from './ProviderForm';
import type { ConfiguredProvider, Driver } from '../../types';

const DRIVER: Driver = {
  id: 'oidc-generic',
  title: 'Generic OIDC',
  schema: {
    issuer: { type: 'string', title: 'Issuer', secret: false },
    client_secret: { type: 'string', title: 'Client secret', secret: true },
  },
};

const PROVIDER: ConfiguredProvider = {
  '@id': '/@identity-providers/dex',
  id: 'dex',
  driver: 'oidc-generic',
  title: 'Dex',
  enabled: true,
  config: { issuer: 'http://dex:5556/dex', client_secret: SECRET_SENTINEL },
};

function renderPanel(
  props: Partial<React.ComponentProps<typeof ProvidersPanel>> = {},
) {
  const onSave = vi.fn();
  const onDelete = vi.fn();
  const onTest = vi.fn();
  render(
    <ProvidersPanel
      providers={[PROVIDER]}
      drivers={[DRIVER]}
      loading={false}
      busy={false}
      onSave={onSave}
      onDelete={onDelete}
      onTest={onTest}
      {...props}
    />,
  );
  return { onSave, onDelete, onTest };
}

describe('ProvidersPanel', () => {
  it('renders the form for the provider driver', () => {
    renderPanel();

    expect(screen.getByLabelText('Issuer')).toBeTruthy();
    expect(screen.getByLabelText('Client secret')).toBeTruthy();
  });

  it('saves the masked secret straight back when it was not touched', () => {
    // S7/I4: this is exactly the round trip that must not overwrite the
    // stored secret with bullets.
    const { onSave } = renderPanel();

    fireEvent.click(screen.getByText('Save'));

    expect(onSave).toHaveBeenCalledWith('dex', {
      issuer: 'http://dex:5556/dex',
      client_secret: SECRET_SENTINEL,
    });
  });

  it('saves an edited value', () => {
    const { onSave } = renderPanel();

    fireEvent.change(screen.getByLabelText('Issuer'), {
      target: { value: 'https://idp.example' },
    });
    fireEvent.click(screen.getByText('Save'));

    expect(onSave).toHaveBeenCalledWith(
      'dex',
      expect.objectContaining({ issuer: 'https://idp.example' }),
    );
  });

  it('runs the connection check', () => {
    const { onTest } = renderPanel();

    fireEvent.click(screen.getByText('Test connection'));

    expect(onTest).toHaveBeenCalledWith('dex');
  });

  it('reports a successful check', () => {
    renderPanel({
      checking: 'dex',
      check: { ok: true, token_endpoint: 'http://dex/token', has_jwks: true },
    });

    expect(screen.getByRole('status').textContent).toContain(
      'http://dex/token',
    );
  });

  it('warns when a provider publishes no key set', () => {
    renderPanel({
      checking: 'dex',
      check: { ok: true, token_endpoint: 'http://dex/token', has_jwks: false },
    });

    expect(screen.getByRole('status').textContent).toContain('no key set');
  });

  it('reports a failed check with the reason', () => {
    renderPanel({
      checking: 'dex',
      check: { ok: false, error: 'could not fetch discovery' },
    });

    expect(screen.getByRole('status').textContent).toContain(
      'could not fetch discovery',
    );
  });

  it('shows a check only against the provider it was run for', () => {
    renderPanel({ checking: 'somebody-else', check: { ok: true } });

    expect(screen.queryByRole('status')).toBeNull();
  });

  it('deletes a provider', () => {
    const { onDelete } = renderPanel();

    fireEvent.click(screen.getByText('Delete'));

    expect(onDelete).toHaveBeenCalledWith('dex');
  });

  it('refuses to edit a provider whose driver is gone', () => {
    // The backend masks every value of an orphaned provider, so there is
    // nothing safe to render and nothing useful to save.
    renderPanel({ drivers: [] });

    expect(screen.getByRole('alert').textContent).toContain('not installed');
    expect((screen.getByText('Save') as HTMLButtonElement).disabled).toBe(true);
    expect(
      (screen.getByText('Test connection') as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it('still allows deleting an orphaned provider', () => {
    // Removing the leftover record is the one repair that makes sense.
    renderPanel({ drivers: [] });

    expect((screen.getByText('Delete') as HTMLButtonElement).disabled).toBe(
      false,
    );
  });

  it('says so while loading', () => {
    renderPanel({ loading: true });

    expect(screen.getByRole('status').textContent).toContain('Loading');
  });

  it('says so when nothing is configured', () => {
    renderPanel({ providers: [] });

    expect(screen.getByText(/No providers are configured/)).toBeTruthy();
  });
});
