import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter, Route } from 'react-router-dom';

import ProvidersControlPanel from './ProvidersControlPanel';
import { DND_LIBRARIES } from './ProvidersTable';
import {
  CONTROLPANEL_PATH,
  PROVIDER_ADD_PATH,
  PROVIDER_EDIT_PATH,
  PROVIDERS_SETTINGS_PATH,
  providerEditUrl,
} from '../../config/routes';
import {
  CONFIGURED,
  DRIVERS,
  LOADED,
  LOADING,
  GROUPS_STATE,
  loadLazyLibraries,
  PROVIDER_SCHEMA,
  USER_FIELDS_STATE,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof ProvidersControlPanel> = {
  title: 'Identity/ControlPanel/ProvidersControlPanel',
  component: ProvidersControlPanel,
};
export default meta;

type Story = StoryObj<typeof ProvidersControlPanel>;

/** The site-wide settings, as `@controlpanels/identity-providers` serves them. */
const SETTINGS = {
  '@id': 'http://localhost:8080/Plone/@controlpanels/identity-providers',
  schema: {
    title: 'Identity providers',
    fieldsets: [{ id: 'default', title: 'Default', fields: ['callback_url'] }],
    properties: {
      callback_url: {
        title: 'Login callback URL',
        description:
          'Absolute URL of the frontend route the provider redirects to.',
        type: 'string',
      },
    },
    required: [],
  },
  data: { callback_url: 'https://example.org/login-identity' },
};

const base = {
  configuredProviders: { ...LOADED, data: CONFIGURED },
  providerFormSchema: { ...LOADED, data: PROVIDER_SCHEMA },
  identityDrivers: { ...LOADED, data: DRIVERS },
  providerCreate: {},
  providerUpdate: {},
  providerDelete: {},
  providerTest: {},
  providersExportable: { ...LOADED, data: true },
  vocabularies: { ...USER_FIELDS_STATE, ...GROUPS_STATE },
  controlpanels: { controlpanel: SETTINGS, get: LOADED },
};

/**
 * Open the panel at one of its routes.
 *
 * Which view the panel shows comes off the route, so a story reaches a form
 * the way a browser does: by being at its address.
 *
 * @param path Where the browser is.
 * @param route The route pattern that address matches.
 * @returns A decorator.
 */
const at =
  (path: string, route: string = path) =>
  (Story: () => ReactNode) => (
    <MemoryRouter initialEntries={[path]}>
      <Route path={route} exact render={() => Story()} />
    </MemoryRouter>
  );

/**
 * The list, with the drag library loaded so every row has its handle.
 *
 * The stories' stores ignore the dispatch that would deliver the library, so
 * the story loads it first and puts it in the store itself.
 */
export const Default: Story = {
  loaders: [
    async () => ({ lazyLibraries: await loadLazyLibraries(DND_LIBRARIES) }),
  ],
  decorators: [
    (Story: () => ReactNode, { loaded }: { loaded: Record<string, any> }) =>
      withStore({ ...base, lazyLibraries: loaded.lazyLibraries })(Story),
    at(CONTROLPANEL_PATH),
  ],
};

/**
 * For somebody a site lets manage the providers and not export them: no
 * export actions, and no warning about them.
 */
export const WithoutExport: Story = {
  decorators: [
    withStore({ ...base, providersExportable: { ...LOADED, data: false } }),
    at(CONTROLPANEL_PATH),
  ],
};

export const Loading: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADING, data: [] } }),
    at(CONTROLPANEL_PATH),
  ],
};

/** A fresh site: the Add action lives in the toolbar, not in the page. */
export const Empty: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADED, data: [] } }),
    at(CONTROLPANEL_PATH),
  ],
};

/** Nothing to configure with, because no add-on registered a driver. */
export const NoDrivers: Story = {
  decorators: [
    withStore({
      ...base,
      configuredProviders: { ...LOADED, data: [] },
      identityDrivers: { ...LOADED, data: [] },
    }),
    at(CONTROLPANEL_PATH),
  ],
};

/** The state that makes every sign-in fail at the last step. */
export const NoCallbackUrl: Story = {
  decorators: [
    withStore({
      ...base,
      controlpanels: {
        controlpanel: { ...SETTINGS, data: { callback_url: '' } },
        get: LOADED,
      },
    }),
    at(CONTROLPANEL_PATH),
  ],
};

/** The site-wide settings, at `/controlpanel/identity-providers/settings`. */
export const Settings: Story = {
  decorators: [withStore(base), at(PROVIDERS_SETTINGS_PATH)],
};

/** The add form, at `/controlpanel/identity-providers/add`. */
export const Adding: Story = {
  decorators: [withStore(base), at(PROVIDER_ADD_PATH)],
};

/** One provider's edit form, at its own route. */
export const Editing: Story = {
  decorators: [
    withStore(base),
    at(providerEditUrl('keycloak'), PROVIDER_EDIT_PATH),
  ],
};

/**
 * An edit route opened before the providers have arrived, as on a reload.
 *
 * The form waits: Volto's form reads its data once, when it mounts.
 */
export const EditingWhileLoading: Story = {
  decorators: [
    withStore({ ...base, configuredProviders: { ...LOADING, data: [] } }),
    at(providerEditUrl('keycloak'), PROVIDER_EDIT_PATH),
  ],
};

/** An edit route naming a provider that does not exist. */
export const UnknownProvider: Story = {
  decorators: [
    withStore(base),
    at(providerEditUrl('nobody'), PROVIDER_EDIT_PATH),
  ],
};
