import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import IdentitiesMenuItem from './IdentitiesMenuItem';
import ProfileMenuItem from './ProfileMenuItem';
import {
  PersonalInformationMenuItem,
  PreferencesMenuItem,
  SiteSetupMenuItem,
} from './UserMenuPlugs';
import { LOADED, USER, withStore } from '../../stories/fixtures';
import { withPersonalTools } from '../../storybook/withUserMenu';

/**
 * Volto's own menu entries, re-registered as plugs.
 *
 * Each renders nothing on its own -- a plug registers a renderer and returns
 * null -- so the stories mount the pluggable that consumes them. What is
 * worth looking at here is the *assembled* list: which entries appear, and
 * in what order.
 */
const meta: Meta<typeof PreferencesMenuItem> = {
  title: 'Identity/UserMenu/UserMenuPlugs',
  component: PreferencesMenuItem,
  decorators: [withPersonalTools],
  parameters: { fullBleed: true },
};
export default meta;

type Story = StoryObj<typeof PreferencesMenuItem>;

const withState = (user: Record<string, unknown>, actions: unknown[] = []) =>
  withStore({
    userProfile: { ...LOADED, data: { ...USER, ...user } },
    actions: { actions: { user: actions } },
  });

/**
 * Every entry the add-on registers, in the menu's own markup.
 *
 * The markup comes from `withPersonalTools` rather than from here: it is
 * Volto's, it has to sit inside `#toolbar` to be styled at all, and five
 * copies of it across these stories is five things to fix when Volto moves
 * one of them.
 */
const menu = () => (
  <PluggablesProvider>
    <PersonalInformationMenuItem />
    <PreferencesMenuItem />
    <SiteSetupMenuItem />
    <IdentitiesMenuItem />
    <ProfileMenuItem />
    <ul>
      <Pluggable
        name="toolbar-user-menu"
        params={{ loadComponent: () => {} }}
      />
    </ul>
  </PluggablesProvider>
);

/**
 * A member with a Profile of their own.
 *
 * "My profile" holds the first slot instead of Volto's Profile link, and
 * "Sign-in methods" comes straight after Preferences because choosing how
 * you get in is one.
 */
export const Member: Story = { render: menu, decorators: [withState({})] };

/** A manager. Site Setup is last: it is about the site, not the person. */
export const Manager: Story = {
  render: menu,
  decorators: [withState({}, [{ id: 'plone_setup' }])],
};

/**
 * A member with no Profile.
 *
 * Volto's Profile link takes its slot back, leading to the member form at
 * `/personal-information`.
 */
export const WithoutTheProfileLayer: Story = {
  render: menu,
  decorators: [withState({ profile_url: null })],
};

/**
 * A user who has a Profile but is not stored as one.
 *
 * The same menu as above, and for the same reason: the member form is where
 * a `source_users` account's fields are edited, whatever else exists.
 */
export const AProfileTheyAreNotStoredIn: Story = {
  render: menu,
  decorators: [withState({ source: 'source_users' })],
};
