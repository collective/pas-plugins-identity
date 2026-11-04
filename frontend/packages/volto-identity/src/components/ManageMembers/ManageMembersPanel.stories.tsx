import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';

import ManageMembersPanel from './ManageMembersPanel';
import type { Candidate } from './AddMembers';
import { groupMember, groupMembersPage } from '../../stories/fixtures';

const DIRECT = [
  groupMember('contractors', 'Contractors', {
    type: 'group',
    through: ['staff'],
  }),
  groupMember('developers', 'Developers', {
    type: 'group',
    through: ['staff'],
  }),
  groupMember('bob', 'Bob Cratchit'),
  groupMember('charlie', 'Charlie Bucket'),
  groupMember('emilia', 'Emilia Galotti', { profile_url: null }),
];

const CANDIDATES: Candidate[] = [
  { id: 'designers', title: 'Designers', type: 'group' },
  {
    id: 'alice',
    title: 'Alice Liddell',
    type: 'user',
    detail: 'alice@example.com',
  },
];

/**
 * Open the story at a URL, in a router that follows clicks.
 *
 * @param url Where the story starts.
 * @returns A Storybook decorator.
 */
const at = (url: string) => (Story: () => ReactNode) => (
  <MemoryRouter initialEntries={[url]}>{Story()}</MemoryRouter>
);

const meta: Meta<typeof ManageMembersPanel> = {
  title: 'Identity/ManageMembers/ManageMembersPanel',
  component: ManageMembersPanel,
  args: {
    title: 'Staff',
    groupId: 'staff',
    groupUrl: '/identity-profiles/staff',
    result: groupMembersPage(DIRECT, { can_manage: true }),
    refused: false,
    query: '',
    candidateQuery: '',
    onCandidateQuery: () => {},
    candidates: [],
    searching: false,
    busy: false,
    onAdd: () => {},
    removing: null,
    onRemove: () => {},
  },
  decorators: [at('/identity-profiles/staff/manage-members')],
};
export default meta;

type Story = StoryObj<typeof ManageMembersPanel>;

/** Nested groups first, then the people in the group itself. */
export const Members: Story = {};

/** More direct members than one page holds. */
export const Paged: Story = {
  args: {
    result: groupMembersPage(DIRECT, { can_manage: true, items_total: 37 }),
  },
  decorators: [at('/identity-profiles/staff/manage-members?page=2')],
};

/** Somebody being looked for, to add. */
export const Adding: Story = {
  args: { candidateQuery: 'ali', candidates: CANDIDATES },
};

/** A member being removed: the other rows wait. */
export const Removing: Story = {
  args: { removing: 'bob' },
};

export const Loading: Story = {
  args: { result: null },
};

/** Nobody is in the group itself, and nothing is nested in it. */
export const Empty: Story = {
  args: { result: groupMembersPage([], { can_manage: true }) },
};

export const NoMatch: Story = {
  args: {
    query: 'zelda',
    result: groupMembersPage([], { can_manage: true }),
  },
  decorators: [at('/identity-profiles/staff/manage-members?q=zelda')],
};

/** Somebody who may read the group but not change it. */
export const Refused: Story = {
  args: { refused: true, result: groupMembersPage(DIRECT) },
};
