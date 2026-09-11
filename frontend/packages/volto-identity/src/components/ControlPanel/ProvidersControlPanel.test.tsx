import {
  afterEach,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest';
import { act, fireEvent, render, screen } from '../../testing';
import { MemoryRouter, Route, Switch } from 'react-router-dom';
import { Provider } from 'react-redux';
import { toast } from 'react-toastify';
import React from 'react';

import ProvidersControlPanel from './ProvidersControlPanel';
import { DND_LIBRARIES } from './ProvidersTable';
import {
  EXPORT_PROVIDERS,
  REORDER_PROVIDERS,
} from '../../constants/ActionTypes';
import { downloadText } from '../../helpers/download';
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
  loadLazyLibraries,
  PROVIDER_SCHEMA,
} from '../../stories/fixtures';

// Kept so a test can ask whether a failure was reported. The rest of the
// module stays real.
vi.mock('react-toastify', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-toastify')>()),
  toast: { success: vi.fn(), error: vi.fn() },
}));

// jsdom saves no files. What the tests ask is what would have been saved.
vi.mock('../../helpers/download', () => ({ downloadText: vi.fn() }));

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
 * @param dispatch What dispatching an action answers.
 * @returns Accessors for where the router is now.
 */
function renderAt(
  path: string,
  overrides: Record<string, unknown> = {},
  dispatch: (action: any) => unknown = (action) => action,
) {
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
    dispatch,
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

  describe('reordering the providers', () => {
    let libraries: Record<string, any>;

    beforeAll(async () => {
      libraries = await loadLazyLibraries(DND_LIBRARIES);
    });

    beforeEach(() => {
      vi.mocked(toast.error).mockClear();
    });

    /**
     * The drag library, keeping the drop handler the list gives it.
     *
     * @returns The `lazyLibraries` slice, and where the handler is kept.
     */
    function keepingTheDrop() {
      const drop: { end?: (event: unknown) => void } = {};
      const Real = libraries.dndKitCore.DndContext;
      const DndContext = (props: any) => {
        drop.end = props.onDragEnd;
        return <Real {...props} />;
      };
      return {
        drop,
        lazyLibraries: {
          ...libraries,
          dndKitCore: { ...libraries.dndKitCore, DndContext },
        },
      };
    }

    /** The provider ids, in the order the rows are on the page. */
    function shown(): string[] {
      return [
        ...document.querySelectorAll<HTMLElement>('tr[data-provider]'),
      ].map((row) => row.dataset.provider as string);
    }

    it('moves the row when it is dropped and saves every position', () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      const sent: any[] = [];
      renderAt(CONTROLPANEL_PATH, { lazyLibraries }, (action) => {
        sent.push(action);
        // Never answered: the row has moved before the backend says a word.
        return action.type === REORDER_PROVIDERS
          ? new Promise(() => {})
          : action;
      });

      act(() =>
        drop.end!({ active: { id: 'github' }, over: { id: 'keycloak' } }),
      );

      expect(shown()).toEqual(['github', 'keycloak']);
      expect(
        sent.find((action) => action.type === REORDER_PROVIDERS)?.request.data,
      ).toEqual({ order: ['github', 'keycloak'] });
    });

    it('puts the row back and says so when the order cannot be saved', async () => {
      const { drop, lazyLibraries } = keepingTheDrop();
      renderAt(CONTROLPANEL_PATH, { lazyLibraries }, (action) =>
        action.type === REORDER_PROVIDERS
          ? Promise.reject(new Error('refused'))
          : action,
      );

      await act(async () =>
        drop.end!({ active: { id: 'github' }, over: { id: 'keycloak' } }),
      );

      expect(shown()).toEqual(['keycloak', 'github']);
      expect(toast.error).toHaveBeenCalledTimes(1);
    });
  });

  describe('exporting the providers', () => {
    const MAY_EXPORT = { providersExportable: { ...LOADED, data: true } };

    beforeEach(() => {
      vi.mocked(downloadText).mockClear();
      vi.mocked(toast.error).mockClear();
    });

    /**
     * A dispatch that answers exports, and records what was sent.
     *
     * @param answer What an export resolves to, or an error it rejects with.
     * @returns The dispatch, and the actions it was given.
     */
    function answering(answer: unknown) {
      const sent: any[] = [];
      const dispatch = (action: any) => {
        sent.push(action);
        if (action.type !== EXPORT_PROVIDERS) {
          return action;
        }
        return answer instanceof Error
          ? Promise.reject(answer)
          : Promise.resolve(answer);
      };
      return { sent, dispatch };
    }

    const exported = (action: any) => action.type === EXPORT_PROVIDERS;

    it('downloads every provider from the toolbar', async () => {
      const { sent, dispatch } = answering({
        filename: 'pas.plugins.identity.providers.xml',
        xml: '<registry/>',
      });
      renderAt(CONTROLPANEL_PATH, MAY_EXPORT, dispatch);

      await act(async () => {
        fireEvent.click(
          screen.getByRole('button', { name: 'Export every provider' }),
        );
      });

      expect(sent.find(exported)?.request.path).toBe(
        '/@identity-providers/@export',
      );
      expect(downloadText).toHaveBeenCalledWith(
        'pas.plugins.identity.providers.xml',
        '<registry/>',
      );
    });

    it('downloads one provider from its row', async () => {
      const { sent, dispatch } = answering({
        provider: 'github',
        filename: 'pas.plugins.identity.providers.github.xml',
        xml: '<registry/>',
      });
      renderAt(CONTROLPANEL_PATH, MAY_EXPORT, dispatch);
      const row = document.querySelector(
        'tr[data-provider="github"]',
      ) as HTMLElement;

      await act(async () => {
        fireEvent.click(row.querySelector('button[aria-label="Export"]')!);
      });

      expect(sent.find(exported)?.request.path).toBe(
        '/@identity-providers/github/export',
      );
      expect(downloadText).toHaveBeenCalledWith(
        'pas.plugins.identity.providers.github.xml',
        '<registry/>',
      );
    });

    it('says beside the actions that the file carries secrets', () => {
      renderAt(CONTROLPANEL_PATH, MAY_EXPORT);

      expect(screen.getByRole('note').textContent).toContain(
        'every client secret in the clear',
      );
    });

    it('offers nothing to somebody who may not export', () => {
      // Managing the providers is not enough: an export is its own permission.
      renderAt(CONTROLPANEL_PATH, {
        providersExportable: { ...LOADED, data: false },
      });

      expect(
        screen.queryByRole('button', { name: 'Export every provider' }),
      ).toBeNull();
      expect(document.querySelector('button[aria-label="Export"]')).toBeNull();
      expect(screen.queryByRole('note')).toBeNull();
    });

    it('saves nothing and says so when the export is refused', async () => {
      const { dispatch } = answering(new Error('refused'));
      renderAt(CONTROLPANEL_PATH, MAY_EXPORT, dispatch);

      await act(async () => {
        fireEvent.click(
          screen.getByRole('button', { name: 'Export every provider' }),
        );
      });

      expect(downloadText).not.toHaveBeenCalled();
      expect(toast.error).toHaveBeenCalledTimes(1);
    });
  });
});
