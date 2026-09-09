/**
 * What a deployment registering into `belowTitle` gets.
 *
 * The badges are `id-plone`'s, which is where the slot came from: the site
 * shows what a person is inside the organisation -- a team, a role -- under
 * their name, and there was nowhere to put it. The component is written here
 * rather than imported because it is the *downstream* half of the example: a
 * project's own component, registered from its `applyConfig`, reading the
 * content it was handed.
 * @module components/Views/BelowTitleSlot.stories
 */
import type { Meta, StoryObj } from '@storybook/react';
import type { Decorator } from '@storybook/react';
import React from 'react';

import config from '@plone/volto/registry';

import BelowTitleSlot from './BelowTitleSlot';
import GroupView from './GroupView';
import ProfileView from './ProfileView';
import {
  LOADED,
  groupContent,
  profileContent,
  withStore,
} from '../../stories/fixtures';

const CONTENT = profileContent({
  '@id': '/identity-profiles/erico',
  id: 'erico',
  login: 'erico@plone.org',
  fullname: 'Érico Andrei',
  description: 'Plone developer, and the person this add-on is written for.',
  group_ids: [
    { token: 'core-team', title: 'Core team' },
    { token: 'foundation', title: 'Foundation member' },
  ],
});

const GROUP = groupContent({
  id: 'core-team',
  title: 'Core team',
  description: 'The people who can merge.',
  group_ids: [{ token: 'staff', title: 'Staff' }],
});

/** A downstream project's component: the groups somebody is in, as chips. */
const Badges = ({ content }: { content: any }) => {
  const terms = content.group_ids ?? [];
  if (!terms.length) {
    return null;
  }
  return (
    <p style={{ display: 'flex', gap: '0.5rem', margin: '0.5rem 0' }}>
      {terms.map((term: { token: string; title: string }) => (
        <span
          key={term.token}
          style={{
            background: '#e8e8e8',
            borderRadius: '1rem',
            fontSize: '0.85rem',
            padding: '0.15rem 0.75rem',
          }}
        >
          {term.title}
        </span>
      ))}
    </p>
  );
};

/**
 * Register `Badges` into the slot, the way a project's `applyConfig` does.
 *
 * Registration is global and a story re-renders, so this registers once and
 * clears the slot when the story unmounts -- otherwise every other story in
 * the session would grow badges of its own.
 */
const ClearOnUnmount = ({ children }: { children: React.ReactNode }) => {
  React.useEffect(
    () => () => {
      delete config.slots.belowTitle;
    },
    [],
  );
  return <>{children}</>;
};

const withBadges: Decorator = (Story) => {
  if (!config.slots.belowTitle?.data?.['identity-badges']?.length) {
    config.registerSlotComponent({
      slot: 'belowTitle',
      name: 'identity-badges',
      component: Badges,
    });
  }
  return (
    <ClearOnUnmount>
      <Story />
    </ClearOnUnmount>
  );
};

const meta: Meta<typeof BelowTitleSlot> = {
  title: 'Identity/Views/BelowTitleSlot',
  component: BelowTitleSlot,
  args: { content: CONTENT },
};
export default meta;

type Story = StoryObj<typeof BelowTitleSlot>;

/** Nothing registered, which is every site until it asks. The slot is empty. */
export const Unused: Story = {};

/** The slot on its own, rendering what a deployment put in it. */
export const WithBadges: Story = {
  decorators: [withBadges],
};

/** Where it lands on a profile: under the name, above the biography. */
export const OnAProfile: StoryObj<typeof ProfileView> = {
  render: (args) => <ProfileView {...(args as any)} />,
  decorators: [withBadges],
};

/** The same slot on a group page, which renders it in the same place. */
export const OnAGroup: StoryObj<typeof GroupView> = {
  args: { content: GROUP as any },
  render: (args) => <GroupView {...(args as any)} />,
  decorators: [
    withBadges,
    withStore({
      groupMembers: {
        ...LOADED,
        data: {
          '@id': '/@group-members/core-team',
          group: 'core-team',
          items_total: 0,
          items: [],
          nested_groups: [],
          parent_groups: [],
        },
      },
    }),
  ],
};
