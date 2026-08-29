import type { Meta, StoryObj } from '@storybook/react';

import GroupView from './GroupView';
import { LOADED, LOADING, withStore } from '../../stories/fixtures';

const CONTENT = {
  '@id': '/identity-profiles/staff',
  id: 'staff',
  title: 'Staff',
  description: 'Everybody who works here.',
};

const MEMBERS = {
  '@id': '/@group-members/staff',
  group: 'staff',
  items_total: 2,
  items: [
    {
      '@id': '/@group-members/staff/alice',
      id: 'alice',
      fullname: 'Alice Liddell',
      login: 'alice@example.com',
      profile_url: '/identity-profiles/alice',
      through: ['developers'],
    },
    {
      '@id': '/@group-members/staff/bob',
      id: 'bob',
      fullname: 'Bob Cratchit',
      login: 'bob@example.com',
      profile_url: '/identity-profiles/bob',
      through: ['staff'],
    },
  ],
  nested_groups: [
    { '@id': '/g/developers', id: 'developers', title: 'Developers' },
  ],
  parent_groups: [{ '@id': '/g/everyone', id: 'everyone', title: 'Everyone' }],
};

const meta: Meta<typeof GroupView> = {
  title: 'Identity/Views/GroupView',
  component: GroupView,
  args: { content: CONTENT },
};
export default meta;

type Story = StoryObj<typeof GroupView>;

/** A group in the middle of a nesting: something above it and below it. */
export const Nested: Story = {
  decorators: [withStore({ groupMembers: { ...LOADED, data: MEMBERS } })],
};

/** A group with nothing nested inside it, which is most of them. */
export const Flat: Story = {
  decorators: [
    withStore({
      groupMembers: {
        ...LOADED,
        data: { ...MEMBERS, nested_groups: [], parent_groups: [] },
      },
    }),
  ],
};

export const Empty: Story = {
  decorators: [
    withStore({
      groupMembers: {
        ...LOADED,
        data: {
          ...MEMBERS,
          items: [],
          nested_groups: [],
          parent_groups: [],
        },
      },
    }),
  ],
};

export const Loading: Story = {
  decorators: [withStore({ groupMembers: LOADING })],
};

/**
 * A visitor who can see the group without being in it.
 *
 * A membership list is personal data about other people, so it is visible to
 * its own members and to somebody who manages users. The page is still a
 * page.
 */
export const MembershipRefused: Story = {
  decorators: [
    withStore({ groupMembers: { loaded: false, error: { status: 403 } } }),
  ],
};
