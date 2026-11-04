import type { Meta, StoryObj } from '@storybook/react';

import MemberResults from './MemberResults';
import { groupMember, groupMembersPage } from '../../../stories/fixtures';

const PEOPLE = [
  groupMember('alice', 'Alice Liddell', { through: ['developers'] }),
  groupMember('charlie', 'Charlie Bucket'),
  groupMember('emilia', 'Emilia Galotti', {
    profile_url: null,
    through: ['developers', 'contractors'],
  }),
];

const meta: Meta<typeof MemberResults> = {
  title: 'Identity/Views/GroupsView/MemberResults',
  component: MemberResults,
  args: { groupId: 'staff', query: '', result: groupMembersPage(PEOPLE) },
};
export default meta;

type Story = StoryObj<typeof MemberResults>;

/** Nobody has searched: the first page of the group. */
export const FirstPage: Story = {};

/** More members than one page holds, so Volto's pagination appears. */
export const Paged: Story = {
  args: { result: groupMembersPage(PEOPLE, { items_total: 42 }) },
};

export const Loading: Story = {
  args: { result: null },
};

export const Searching: Story = {
  args: { query: 'ali', result: null },
};

export const Found: Story = {
  args: { query: 'li' },
};

export const NoMatch: Story = {
  args: { query: 'zelda', result: groupMembersPage([]) },
};
