import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter } from 'react-router-dom';

import ManageMembers from './ManageMembers';
import {
  groupContent,
  groupMember,
  groupMembersPage,
  LOADED,
  LOADING,
  withStore,
} from '../../stories/fixtures';

const DIRECT = [
  groupMember('developers', 'Developers', {
    type: 'group',
    through: ['staff'],
  }),
  groupMember('bob', 'Bob Cratchit'),
  groupMember('charlie', 'Charlie Bucket'),
];

/** What Volto loaded for the URL without `/manage-members`. */
const CONTENT = { data: groupContent() };

/** Volto's own slots, as `listUsers` and `listGroups` fill them. */
const NO_SEARCH = {
  users: { users: [], list: LOADED },
  groups: { groups: [], list: LOADED },
};

/**
 * Open the page at a URL.
 *
 * @param url Where the page is open.
 * @returns A Storybook decorator.
 */
const at = (url: string) => (Story: () => ReactNode) => (
  <MemoryRouter initialEntries={[url]}>{Story()}</MemoryRouter>
);

const meta: Meta<typeof ManageMembers> = {
  title: 'Identity/ManageMembers/ManageMembers',
  component: ManageMembers,
};
export default meta;

type Story = StoryObj<typeof ManageMembers>;

/** The whole page, as a Manager opens it from the group. */
export const Default: Story = {
  decorators: [
    withStore({
      ...NO_SEARCH,
      content: CONTENT,
      groupDirectMembers: {
        ...LOADED,
        data: groupMembersPage(DIRECT, { can_manage: true, items_total: 23 }),
      },
    }),
    at('/identity-profiles/staff/manage-members'),
  ],
};

export const Loading: Story = {
  decorators: [
    withStore({ ...NO_SEARCH, content: CONTENT, groupDirectMembers: LOADING }),
    at('/identity-profiles/staff/manage-members'),
  ],
};

/** A member of the group, who may read it and not change it. */
export const Refused: Story = {
  decorators: [
    withStore({
      ...NO_SEARCH,
      content: CONTENT,
      groupDirectMembers: { ...LOADED, data: groupMembersPage(DIRECT) },
    }),
    at('/identity-profiles/staff/manage-members'),
  ],
};
