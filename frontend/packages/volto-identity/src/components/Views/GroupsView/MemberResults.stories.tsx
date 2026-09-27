import type { Meta, StoryObj } from '@storybook/react';

import MemberResults from './MemberResults';
import type { GroupMember, GroupMembers } from '../../../types';

const PEOPLE: GroupMember[] = [
  {
    '@id': '/identity-profiles/alice',
    id: 'alice',
    fullname: 'Alice Liddell',
    login: 'alice@example.com',
    profile_url: '/identity-profiles/alice',
    through: ['developers'],
  },
  {
    '@id': '/identity-profiles/charlie',
    id: 'charlie',
    fullname: 'Charlie Bucket',
    login: 'charlie@example.com',
    profile_url: '/identity-profiles/charlie',
    through: ['staff'],
  },
  {
    '@id': '/identity-profiles/emilia',
    id: 'emilia',
    fullname: 'Emilia Galotti',
    login: 'emilia@example.com',
    profile_url: null,
    through: ['developers', 'contractors'],
  },
];

/**
 * A search answered with `items`.
 *
 * @param items The rows on the first page.
 * @param total How many matched in all.
 * @returns The listing.
 */
function found(items: GroupMember[], total = items.length): GroupMembers {
  return {
    '@id': '/@group-members/staff',
    group: 'staff',
    items,
    items_total: total,
    members_total: 42,
    direct_members_total: 12,
    nested_groups: [],
    parent_groups: [],
  };
}

const meta: Meta<typeof MemberResults> = {
  title: 'Identity/Views/GroupsView/MemberResults',
  component: MemberResults,
  args: { groupId: 'staff', query: 'li', result: found(PEOPLE) },
};
export default meta;

type Story = StoryObj<typeof MemberResults>;

/** Nobody has searched yet. */
export const BeforeSearching: Story = {
  args: { query: '', result: null },
};

export const Searching: Story = {
  args: { query: 'ali', result: null },
};

export const Found: Story = {};

/** More matches than one page holds. */
export const Partial: Story = {
  args: { query: 'example', result: found(PEOPLE, 31) },
};

export const NoMatch: Story = {
  args: { query: 'zelda', result: found([]) },
};
