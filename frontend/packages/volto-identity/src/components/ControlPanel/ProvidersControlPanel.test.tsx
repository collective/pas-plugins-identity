import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '../../testing';
import { MemoryRouter, Route, Switch } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import ProvidersControlPanel from './ProvidersControlPanel';
import install, {
  CONTROLPANEL_PATH,
  PROVIDER_ADD_PATH,
  PROVIDERS_SETTINGS_PATH,
  providerEditUrl,
} from '../../config/routes';
import {
  CONFIGURED,
  DRIVERS,
  LOADED,
  LOADING,
  PROVIDER_SCHEMA,
} from '../../stories/fixtures';

// The toolbar reads store slices this page does not own, so it is replaced by
// one that renders what the panel puts in it: the actions under test live
// there. `vi.mock` is hoisted above the imports, which is why the factories
// import React for themselves.
vi.mock('@plone/volto/components/manage/Toolbar/Toolbar', async () => {
  const react = await import('react');
  return {
    default: ({ inner }: { inner: React.ReactNode }) =>
      react.createElement('nav', { 'aria-label': 'Toolbar' }, inner),
  };
});

// Volto's form needs most of a running site. What these tests ask is which
// form the route opened, and the title says that.
vi.mock('@plone/volto/components/manage/Form', async () => {
  const react = await import('react');
  return {
    Form: react.forwardRef((props: { title?: string }, _ref) =>
      react.createElement('form', { 'aria-label': props.title }),
    ),
  };
});

/** The site-wide settings, as `@controlpanels/identity-providers` serves them. */
const SETTINGS = {
  '@id': 'http://localhost:8080/Plone/@controlpanels/identity-providers',
  schema: {
    title: 'Identity providers',
    fieldsets: [{ id: 'default', title: 'Default', fields: ['callback_url'] }],
    properties: {
      callback_url: { title: 'Login callback URL', type: 'string' },
    },
    required: [],
  },
  data: { callback_url: 'https://example.org/login-identity' },
};

/**
 * The panel's routes, exactly as the add-on registers them.
 *
 * Taken from the install step rather than restated, so a route that is not
 * registered is a route these tests cannot reach.
 */
function panelRoutes(): any[] {
  const config: any = { settings: { nonContentRoutes: [] }, addonRoutes: [] };
  install(config);
  return config.addonRoutes.filter(
    (route: any) => route.component === ProvidersControlPanel,
  );
}

/**
 * Render the panel at a path, the way the application routes to it.
 *
 * @param path Where the browser is.
 * @param overrides Store slices to replace.
 * @returns Accessors for where the router is now.
 */
function renderAt(path: string, overrides: Record<string, unknown> = {}) {
  const state = {
    configuredProviders: { ...LOADED, data: CONFIGURED },
    providerFormSchema: { ...LOADED, data: PROVIDER_SCHEMA },
    identityDrivers: { ...LOADED, data: DRIVERS },
    providerTest: {},
    controlpanels: { controlpanel: SETTINGS, get: LOADED },
    ...overrides,
  };
  const store = {
    getState: () => state,
    dispatch: (action: any) => action,
    subscribe: () => () => {},
  };
  const router: { location?: any; history?: any } = {};
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={[path]}>
        <Switch>
          {panelRoutes().map((route, index) => (
            <Route key={index} {...route} />
          ))}
        </Switch>
        <Route
          render={({ location, history }) => {
            router.location = location;
            router.history = history;
            return null;
          }}
        />
      </MemoryRouter>
    </Provider>,
  );
  return router;
}

describe('ProvidersControlPanel', () => {
  beforeEach(() => {
    const toolbar = document.createElement('div');
    toolbar.id = 'toolbar';
    document.body.appendChild(toolbar);
  });

  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  describe('each view has a route', () => {
    it('lists the providers at the panel itself', () => {
      renderAt(CONTROLPANEL_PATH);

      expect(screen.getByText('Sign in with Keycloak')).toBeTruthy();
      expect(screen.queryByRole('form')).toBeNull();
    });

    it('opens the settings form at its route', () => {
      renderAt(PROVIDERS_SETTINGS_PATH);

      expect(screen.getByRole('form', { name: 'Settings' })).toBeTruthy();
    });

    it('opens the add form at its route', () => {
      renderAt(PROVIDER_ADD_PATH);

      expect(screen.getByRole('form', { name: 'Add provider' })).toBeTruthy();
    });

    it("opens a provider's edit form at its route", () => {
      // Which is also what a reload of that form does.
      renderAt(providerEditUrl('github'));

      expect(screen.getByRole('form', { name: 'GitHub' })).toBeTruthy();
    });

    it('edits a provider called settings rather than opening the settings', () => {
      const named = {
        ...CONFIGURED[1],
        '@id': '/@identity-providers/settings',
        id: 'settings',
        title: 'A provider called settings',
      };

      renderAt(providerEditUrl('settings'), {
        configuredProviders: { ...LOADED, data: [...CONFIGURED, named] },
      });

      expect(
        screen.getByRole('form', { name: 'A provider called settings' }),
      ).toBeTruthy();
    });
  });

  describe('a form opened before its data has arrived', () => {
    it('waits rather than mounting an empty form', () => {
      // Volto's form reads its data once, when it mounts, so a form opened on
      // a reload before the providers arrive would stay empty after they do.
      renderAt(providerEditUrl('github'), {
        configuredProviders: { ...LOADING, data: [] },
      });

      expect(screen.queryByRole('form')).toBeNull();
      expect(screen.getByRole('status')).toBeTruthy();
    });

    it('says so when no provider has the id', () => {
      renderAt(providerEditUrl('nobody'));

      expect(screen.getByRole('alert').textContent).toContain('nobody');
      expect(
        screen
          .getByRole('link', { name: 'Back to the providers' })
          .getAttribute('href'),
      ).toBe(CONTROLPANEL_PATH);
    });

    it('offers no Save for a form that is not there', () => {
      renderAt(providerEditUrl('nobody'));

      expect(screen.queryByRole('button', { name: 'Save' })).toBeNull();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy();
    });
  });

  describe('moving between the views', () => {
    it("links each row to that provider's edit form", () => {
      const router = renderAt(CONTROLPANEL_PATH);

      const row = document.querySelector('tr[data-provider="github"]');
      fireEvent.click(row!.querySelector('a[aria-label="Edit"]')!);

      expect(router.location.pathname).toBe(providerEditUrl('github'));
    });

    it('reaches the settings from the toolbar', () => {
      const router = renderAt(CONTROLPANEL_PATH);

      fireEvent.click(screen.getByRole('link', { name: 'Settings' }));

      expect(router.location.pathname).toBe(PROVIDERS_SETTINGS_PATH);
    });

    it('reaches the add form from the toolbar', () => {
      const router = renderAt(CONTROLPANEL_PATH);

      fireEvent.click(screen.getByRole('link', { name: 'Add provider' }));

      expect(router.location.pathname).toBe(PROVIDER_ADD_PATH);
    });

    it('returns to the list on cancel', () => {
      const router = renderAt(providerEditUrl('github'));

      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

      expect(router.location.pathname).toBe(CONTROLPANEL_PATH);
    });

    it('comes back to the list with the Back button', () => {
      // The complaint the routes fix: with the form as component state there
      // was no history entry to return to, so Back left the control panel.
      const router = renderAt(CONTROLPANEL_PATH);
      fireEvent.click(screen.getByRole('link', { name: 'Settings' }));

      act(() => router.history.goBack());

      expect(router.location.pathname).toBe(CONTROLPANEL_PATH);
      expect(screen.getByText('Sign in with Keycloak')).toBeTruthy();
    });
  });
});
