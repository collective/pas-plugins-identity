import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import { PluggablesProvider } from '@plone/volto/components/manage/Pluggable';
import PersonalTools from './PersonalTools';
import IdentitiesMenuItem from '../../../../../components/UserMenu/IdentitiesMenuItem';
import ProfileMenuItem from '../../../../../components/UserMenu/ProfileMenuItem';
import {
  PersonalInformationMenuItem,
  PreferencesMenuItem,
  SiteSetupMenuItem,
} from '../../../../../components/UserMenu/UserMenuPlugs';
import { LOADED, USER, withStore } from '../../../../../stories/fixtures';

/**
 * The shadowed personal-tools menu.
 *
 * Worth a story even though it is Volto's component: it is this package's
 * code now, and these stories are where the entries are seen *in place*
 * rather than each on its own. Every entry is a plug, so a story that mounts
 * none of them renders an empty menu -- which is itself worth seeing, since
 * that is what a site removing them all would get.
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

/** Everything the add-on registers, which is the whole menu. */
const Menu = (args: React.ComponentProps<typeof PersonalTools>) => (
  <PluggablesProvider>
    <PersonalInformationMenuItem />
    <PreferencesMenuItem />
    <SiteSetupMenuItem />
    <IdentitiesMenuItem />
    <ProfileMenuItem />
    <PersonalTools {...args} />
  </PluggablesProvider>
);

/** An ordinary member: no Site Setup, and "My profile" in the first slot. */
export const Member: Story = {
  render: (args) => <Menu {...args} />,
  decorators: [withState({})],
};

/** A manager, who also gets Site Setup — last, because it is about the site. */
export const Manager: Story = {
  render: (args) => <Menu {...args} />,
  decorators: [withState({}, [{ id: 'plone_setup' }])],
};

/**
 * A site without the `[profile]` layer: Volto's own Profile link takes the
 * slot back, leading to the member form at `/personal-information`.
 *
 * "Sign-in methods" stays, because identities are core rather than part of
 * the optional layer.
 */
export const WithoutTheProfileLayer: Story = {
  render: (args) => <Menu {...args} />,
  decorators: [withState({ profile_url: null })],
};

/**
 * A user with no name yet. The header shows the userid rather than nothing:
 * an empty header reads as a broken menu.
 */
export const NameNotLoadedYet: Story = {
  render: (args) => <Menu {...args} />,
  decorators: [withState({ fullname: null, username: null })],
};

/**
 * The component on its own, with nothing plugged in.
 *
 * Not a state a running site is in -- the add-on registers five entries --
 * but it is what this component actually contributes: the header, the width,
 * and an empty list.
 */
export const NothingPluggedIn: Story = {
  render: (args) => (
    <PluggablesProvider>
      <PersonalTools {...args} />
    </PluggablesProvider>
  ),
  decorators: [withState({})],
};
