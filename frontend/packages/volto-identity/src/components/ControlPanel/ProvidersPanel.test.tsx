import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { IntlProvider } from 'react-intl';
import { Provider } from 'react-redux';
import React from 'react';

import ProvidersPanel from './ProvidersPanel';
import { SECRET_SENTINEL } from './ProviderForm';
import type { ConfiguredProvider, Driver } from '../../types';

/**
 * react-intl 3.x predates React 18's typing of `children`, so its
 * `IntlProvider` is not assignable as written. The component works; only
 * the declaration is behind.
 */
const Intl = IntlProvider as unknown as React.FC<{
  locale: string;
  children: React.ReactNode;
}>;

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
  propertymap: { login: 'username' },
};

/**
 * The panel embeds Volto's ObjectListWidget for the property map, which
 * needs intl and the store it has in the real control panel.
 */
function wrapper(children: React.ReactNode) {
  const store = {
    getState: () => ({
      vocabularies: {},
      intl: { locale: 'en', messages: {} },
    }),
    dispatch: (action: any) => action,
    subscribe: () => () => {},
  };
  return (
    <Provider store={store as any}>
      <Intl locale="en">{children}</Intl>
    </Provider>
  );
}

function renderPanel(
  props: Partial<React.ComponentProps<typeof ProvidersPanel>> = {},
) {
  const onCreate = vi.fn();
  const onSave = vi.fn();
  const onDelete = vi.fn();
  const onTest = vi.fn();
  render(
    wrapper(
      <ProvidersPanel
        providers={[PROVIDER]}
        drivers={[DRIVER]}
        loading={false}
        busy={false}
        onCreate={onCreate}
        onSave={onSave}
        onDelete={onDelete}
        onTest={onTest}
        {...props}
      />,
    ),
  );
  return { onCreate, onSave, onDelete, onTest };
}

describe('ProvidersPanel', () => {
  it('renders the form for the provider driver', () => {
    renderPanel();

    expect(
      screen.getByLabelText('Issuer', {
        selector: '#identity-field-dex-issuer',
      }),
    ).toBeTruthy();
    expect(
      screen.getByLabelText('Client secret', {
        selector: '#identity-field-dex-client_secret',
      }),
    ).toBeTruthy();
  });

  it('saves the masked secret straight back when it was not touched', () => {
    // This is exactly the round trip that must not overwrite the
    // stored secret with bullets.
    const { onSave } = renderPanel();

    fireEvent.click(screen.getByText('Save'));

    expect(onSave).toHaveBeenCalledWith('dex', {
      title: 'Dex',
      enabled: true,
      config: {
        issuer: 'http://dex:5556/dex',
        client_secret: SECRET_SENTINEL,
      },
      propertymap: { login: 'username' },
    });
  });

  it('saves an edited value', () => {
    const { onSave } = renderPanel();

    fireEvent.change(
      screen.getByLabelText('Issuer', {
        selector: '#identity-field-dex-issuer',
      }),
      { target: { value: 'https://idp.example' } },
    );
    fireEvent.click(screen.getByText('Save'));

    expect(onSave).toHaveBeenCalledWith(
      'dex',
      expect.objectContaining({
        config: expect.objectContaining({ issuer: 'https://idp.example' }),
      }),
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

  it('offers the add form on a site with nothing configured', () => {
    // The state every fresh site starts in. Without this the panel is a
    // dead end: nothing to edit, and no way to make something to edit.
    renderPanel({ providers: [] });

    expect(screen.getByLabelText(/Provider ID/)).toBeTruthy();
    expect(screen.getByText('Add provider')).toBeTruthy();
  });

  it('creates a provider from the form', () => {
    const { onCreate } = renderPanel({ providers: [] });

    fireEvent.change(screen.getByLabelText(/Provider ID/), {
      target: { value: 'keycloak' },
    });
    fireEvent.change(screen.getByLabelText(/Driver/), {
      target: { value: 'oidc-generic' },
    });
    fireEvent.change(screen.getByLabelText(/Title/), {
      target: { value: 'Keycloak' },
    });
    fireEvent.change(
      screen.getByLabelText('Issuer', {
        selector: '#identity-field-new-issuer',
      }),
      { target: { value: 'https://kc.example/realms/main' } },
    );
    fireEvent.click(screen.getByText('Add provider'));

    expect(onCreate).toHaveBeenCalledWith({
      id: 'keycloak',
      driver: 'oidc-generic',
      title: 'Keycloak',
      enabled: true,
      config: { issuer: 'https://kc.example/realms/main' },
      propertymap: {},
    });
  });

  it('shows the driver schema only once a driver is chosen', () => {
    // Which fields exist depends on the driver, so there is nothing
    // honest to render before one is picked.
    renderPanel({ providers: [] });

    expect(screen.queryByLabelText('Issuer')).toBeNull();

    fireEvent.change(screen.getByLabelText(/Driver/), {
      target: { value: 'oidc-generic' },
    });

    expect(screen.getByLabelText('Issuer')).toBeTruthy();
  });

  it('forgets config typed against a driver that was swapped out', () => {
    const { onCreate } = renderPanel({
      providers: [],
      drivers: [DRIVER, { id: 'other', title: 'Other', schema: {} }],
    });

    fireEvent.change(screen.getByLabelText(/Provider ID/), {
      target: { value: 'x' },
    });
    fireEvent.change(screen.getByLabelText(/Driver/), {
      target: { value: 'oidc-generic' },
    });
    fireEvent.change(screen.getByLabelText('Issuer'), {
      target: { value: 'https://kc.example' },
    });
    fireEvent.change(screen.getByLabelText(/Driver/), {
      target: { value: 'other' },
    });
    fireEvent.click(screen.getByText('Add provider'));

    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({ driver: 'other', config: {} }),
    );
  });

  it('cannot submit before a driver is chosen', () => {
    renderPanel({ providers: [] });

    expect(
      (screen.getByText('Add provider') as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it('says so when no driver is installed at all', () => {
    renderPanel({ providers: [], drivers: [] });

    expect(screen.getByText(/No drivers are installed/)).toBeTruthy();
    expect(screen.queryByText('Add provider')).toBeNull();
  });

  it('edits a title and an enabled flag', () => {
    const { onSave } = renderPanel();

    fireEvent.change(
      screen.getByLabelText('Title', { selector: '#identity-title-dex' }),
      { target: { value: 'Company SSO' } },
    );
    fireEvent.click(
      screen.getByLabelText('Enabled', { selector: '#identity-enabled-dex' }),
    );
    fireEvent.click(screen.getByText('Save'));

    expect(onSave).toHaveBeenCalledWith(
      'dex',
      expect.objectContaining({ title: 'Company SSO', enabled: false }),
    );
  });

  it('carries an existing map through an unrelated save', () => {
    // The map is not what this save is about; it must still survive.
    const { onSave } = renderPanel();

    fireEvent.change(
      screen.getByLabelText('Title', { selector: '#identity-title-dex' }),
      { target: { value: 'Renamed' } },
    );
    fireEvent.click(screen.getByText('Save'));

    const [, data] = onSave.mock.calls[0];
    expect(data.propertymap).toEqual({ login: 'username' });
  });

  it('keeps title and enabled out of the config it sends', () => {
    // They live beside the config on the record, and the backend would
    // otherwise store them as driver settings that no driver declares.
    const { onSave } = renderPanel();

    fireEvent.change(
      screen.getByLabelText('Title', { selector: '#identity-title-dex' }),
      { target: { value: 'Company SSO' } },
    );
    fireEvent.click(screen.getByText('Save'));

    const [, data] = onSave.mock.calls[0];
    expect(Object.keys(data.config as object)).toEqual([
      'issuer',
      'client_secret',
    ]);
  });
});
