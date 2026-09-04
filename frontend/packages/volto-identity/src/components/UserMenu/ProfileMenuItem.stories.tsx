import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import {
  Pluggable,
  PluggablesProvider,
} from '@plone/volto/components/manage/Pluggable';
import ProfileMenuItem from './ProfileMenuItem';
import { withPersonalTools } from '../../storybook/withUserMenu';
import { withUser } from '../../stories/fixtures';

const meta: Meta<typeof ProfileMenuItem> = {
  title: 'Identity/UserMenu/ProfileMenuItem',
  component: ProfileMenuItem,
  decorators: [withPersonalTools],
  parameters: { fullBleed: true },
};
export default meta;

type Story = StoryObj<typeof ProfileMenuItem>;

/**
 * The plug renders nothing on its own -- it registers a renderer -- so every
 * story has to include the pluggable that consumes it, the way Volto's user
 * menu does.
 */
const inTheMenu = () => (
  <PluggablesProvider>
    <ProfileMenuItem />
    <ul>
      <Pluggable name="toolbar-user-menu" />
    </ul>
  </PluggablesProvider>
);

/** A user whose account *is* a Profile content object. */
export const StoredAsAProfile: Story = {
  render: inTheMenu,
  decorators: [
    withUser({ profile_url: 'https://example.org/identity-profiles/alice' }),
  ],
};

/**
 * A user who *has* a Profile but is not stored as one.
 *
 * Their account lives in `source_users`, so `/personal-information` is still
 * where their fields are edited and Volto's own Profile entry keeps the slot.
 */
export const StoredElsewhere: Story = {
  render: inTheMenu,
  decorators: [
    withUser({
      source: 'source_users',
      profile_url: 'https://example.org/identity-profiles/alice',
    }),
  ],
};

/**
 * No Profile: the entry is absent rather than disabled.
 *
 * Either this account predates the add-on, or first login has not minted a
 * Profile for it yet. A menu entry leading nowhere is worse than no menu
 * entry, which is why this renders an empty list.
 */
export const WithoutAProfile: Story = {
  render: inTheMenu,
  decorators: [withUser({ profile_url: null })],
};

/** Before the user has loaded, there is nothing to decide on yet. */
export const Anonymous: Story = {
  render: inTheMenu,
  decorators: [withUser(null)],
};
