import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import PersonalTools from './PersonalTools';
import IdentitiesMenuItem from '../../../../../components/UserMenu/IdentitiesMenuItem';
import ProfileMenuItem from '../../../../../components/UserMenu/ProfileMenuItem';
import { LOADED, USER, withStore } from '../../../../../stories/fixtures';

/**
 * The shadowed personal-tools menu.
 *
 * Worth a story even though it is Volto's component: it is this package's
 * code now, and these stories are where the two entries this add-on plugs
 * into it are seen *in place* rather than each on its own.
 *
 * The menu is normally sized to the toolbar it slides over, which is not
 * here -- `theToolbar` is an empty ref, so it takes its natural width.
 */
const meta: Meta<typeof PersonalTools> = {
  title: 'Identity/UserMenu/PersonalTools',
  component: PersonalTools,
  args: {
    loadComponent: () => {},
    unloadComponent: () => {},
    theToolbar: { current: null },
  },
};
export default meta;

type Story = StoryObj<typeof PersonalTools>;

const withState = (user: Record<string, unknown>, actions: unknown[] = []) =>
  withStore({
    userProfile: { ...LOADED, data: { ...USER, ...user } },
    actions: { actions: { user: actions } },
  });

/** An ordinary member: no Site Setup, and this add-on's two entries. */
export const Member: Story = {
  render: (args) => (
    <PluggablesProvider>
      <IdentitiesMenuItem />
      <ProfileMenuItem />
      <PersonalTools {...args} />
    </PluggablesProvider>
  ),
  decorators: [withState({})],
};

/** A manager, who also gets Site Setup. */
export const Manager: Story = {
  render: (args) => (
    <PluggablesProvider>
      <IdentitiesMenuItem />
      <ProfileMenuItem />
      <PersonalTools {...args} />
    </PluggablesProvider>
  ),
  decorators: [withState({}, [{ id: 'plone_setup' }])],
};

/**
 * A site without the `[profile]` layer: no "My profile" entry.
 *
 * "Sign-in methods" stays, because identities are core rather than part of
 * the optional layer.
 */
export const WithoutTheProfileLayer: Story = {
  render: (args) => (
    <PluggablesProvider>
      <IdentitiesMenuItem />
      <ProfileMenuItem />
      <PersonalTools {...args} />
    </PluggablesProvider>
  ),
  decorators: [withState({ profile_url: null })],
};

/**
 * A user with no name yet. The header shows the userid rather than nothing:
 * an empty header reads as a broken menu.
 */
export const NameNotLoadedYet: Story = {
  render: (args) => (
    <PluggablesProvider>
      <PersonalTools {...args} />
    </PluggablesProvider>
  ),
  decorators: [withState({ fullname: null, username: null })],
};

/** Bare, without this add-on's entries: what upstream renders, minus the avatar. */
export const WithoutTheAddonEntries: Story = {
  render: (args) => (
    <PluggablesProvider>
      <PersonalTools {...args} />
      <Pluggable name="toolbar-user-menu" />
    </PluggablesProvider>
  ),
  decorators: [withState({})],
};
