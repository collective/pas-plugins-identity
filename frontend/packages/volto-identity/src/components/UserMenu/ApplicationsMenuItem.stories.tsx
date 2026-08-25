import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import ApplicationsMenuItem from './ApplicationsMenuItem';
import { LOADED, USER, withStore } from '../../stories/fixtures';

const meta: Meta<typeof ApplicationsMenuItem> = {
  title: 'Identity/UserMenu/ApplicationsMenuItem',
  component: ApplicationsMenuItem,
};
export default meta;

type Story = StoryObj<typeof ApplicationsMenuItem>;

/**
 * The plug renders nothing on its own -- it registers a renderer -- so every
 * story includes the pluggable that consumes it, the way the user menu does.
 */
const inTheMenu = () => (
  <MemoryRouter>
    <PluggablesProvider>
      <ApplicationsMenuItem />
      <ul>
        <Pluggable name="toolbar-user-menu" />
      </ul>
    </PluggablesProvider>
  </MemoryRouter>
);

const withGrants = (grants: Record<string, unknown>) =>
  withStore({
    userProfile: { ...LOADED, data: USER },
    oauthGrants: grants,
  });

/** A site running the `[server]` layer: the endpoint answered. */
export const OnAnAuthorizationServer: Story = {
  render: inTheMenu,
  decorators: [withGrants({ ...LOADED, data: { items: [] } })],
};

/**
 * A site without that layer.
 *
 * Nothing publishes `@oauth-grants` there, so the entry is absent rather
 * than leading to a page that can only report a failure.
 */
export const OnAnOrdinarySite: Story = {
  render: inTheMenu,
  decorators: [withGrants({ loaded: false, error: new Error('404') })],
};

/** Before the answer arrives. */
export const StillAsking: Story = {
  render: inTheMenu,
  decorators: [withGrants({ loading: true, loaded: false, error: null })],
};
