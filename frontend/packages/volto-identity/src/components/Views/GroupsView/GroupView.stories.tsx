import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import { StaticRouter } from 'react-router-dom';

import GroupView from './GroupView';
import { groupContent } from '../../../stories/fixtures';
import { LOADED, LOADING, withStore } from '../../../stories/fixtures';
import type { GroupMember, GroupMembers } from '../../../types';

const CONTENT = groupContent({
  description: 'Everybody who works here.',
});

const ALICE: GroupMember = {
  '@id': '/@group-members/staff/alice',
  id: 'alice',
  fullname: 'Alice Liddell',
  login: 'alice@example.com',
  profile_url: '/identity-profiles/alice',
  through: ['developers'],
  type: 'user',
};

const CHARLIE: GroupMember = {
  '@id': '/@group-members/staff/charlie',
  id: 'charlie',
  fullname: 'Charlie Bucket',
  login: 'charlie@example.com',
  profile_url: '/identity-profiles/charlie',
  through: ['staff'],
  type: 'user',
};

const EMILIA: GroupMember = {
  '@id': '/@group-members/staff/emilia',
  id: 'emilia',
  fullname: 'Emilia Galotti',
  login: 'emilia@example.com',
  profile_url: null,
  through: ['developers', 'contractors'],
  type: 'user',
};

/** The group's summary: how big it is and where it sits. */
const SUMMARY: GroupMembers = {
  '@id': '/@group-members/staff',
  group: 'staff',
  items_total: 42,
  items: [],
  members_total: 42,
  direct_members_total: 12,
  nested_groups: [
    {
      '@id': '/@group-members/developers',
      id: 'developers',
      title: 'Developers',
      group_url: '/identity-groups/developers',
    },
    {
      '@id': '/@group-members/contractors',
      id: 'contractors',
      title: 'Contractors',
      group_url: '/identity-groups/contractors',
    },
  ],
  parent_groups: [
    {
      '@id': '/@group-members/everyone',
      id: 'everyone',
      title: 'Everyone',
      group_url: '/identity-groups/everyone',
    },
  ],
  can_manage: false,
};

/** A group with nothing nested in it: everybody is a direct member. */
const FLAT: GroupMembers = {
  ...SUMMARY,
  items_total: 8,
  members_total: 8,
  direct_members_total: 8,
  nested_groups: [],
  parent_groups: [],
};

/**
 * Open the page at a URL, the way a linked search or page arrives.
 *
 * Storybook's preview puts every story at `/`; the search and the page are
 * read from the query string, so a story showing one needs a location of its
 * own.
 *
 * @param url The location to render at.
 * @returns The decorator.
 */
function atLocation(url: string) {
  const Decorator = (Story: () => ReactNode) => (
    <StaticRouter location={url}>{Story()}</StaticRouter>
  );
  return Decorator;
}

/**
 * A page of members, out of `total`.
 *
 * @param items The members on this page.
 * @param total How many there are on every page together.
 * @returns The listing slot's data.
 */
function page(items: GroupMember[], total = items.length) {
  return { ...SUMMARY, items, items_total: total };
}

const meta: Meta<typeof GroupView> = {
  title: 'Identity/Views/GroupsView/GroupView',
  component: GroupView,
  args: { content: CONTENT },
};
export default meta;

type Story = StoryObj<typeof GroupView>;

/**
 * A group in the middle of a nesting, as it opens.
 *
 * How many people are in it, how many of them directly, and the first page
 * of them, with a search to narrow it and Volto's pagination for the rest.
 */
export const Nested: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: {
        ...LOADED,
        data: page([ALICE, CHARLIE, EMILIA], 42),
      },
    }),
    atLocation('/identity-groups/staff'),
  ],
};

/** The third of five pages, as a link to it opens. */
export const ThirdPage: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: {
        ...LOADED,
        data: page([ALICE, CHARLIE, EMILIA], 42),
      },
    }),
    atLocation('/identity-groups/staff?page=3'),
  ],
};

/**
 * A group with nothing nested inside it, which is most of them.
 *
 * Everybody is a direct member, so the count does not split, and one page
 * holds them all, so there is no pagination.
 */
export const Flat: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: FLAT },
      groupMemberSearch: { ...LOADED, data: page([CHARLIE], 1) },
    }),
    atLocation('/identity-groups/staff'),
  ],
};

/**
 * Somebody who may change the members, who is offered the page that does.
 */
export const Manageable: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: { ...SUMMARY, can_manage: true } },
      groupMemberSearch: {
        ...LOADED,
        data: page([ALICE, CHARLIE, EMILIA], 42),
      },
    }),
    atLocation('/identity-groups/staff'),
  ],
};

/** A search, answered. A member who came in through another group says so. */
export const SearchResults: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: {
        ...LOADED,
        data: page([ALICE, CHARLIE, EMILIA]),
      },
    }),
    atLocation('/identity-groups/staff?q=li'),
  ],
};

/** More matches than one page holds: the search is paged as well. */
export const SearchResultsPaged: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: {
        ...LOADED,
        data: page([ALICE, CHARLIE, EMILIA], 31),
      },
    }),
    atLocation('/identity-groups/staff?q=example'),
  ],
};

/** A search on its way. The counts stay on screen while it is. */
export const Searching: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: LOADING,
    }),
    atLocation('/identity-groups/staff?q=ali'),
  ],
};

export const NoMatch: Story = {
  decorators: [
    withStore({
      groupMembers: { ...LOADED, data: SUMMARY },
      groupMemberSearch: { ...LOADED, data: page([]) },
    }),
    atLocation('/identity-groups/staff?q=zelda'),
  ],
};

/** Nobody in it yet: nothing to list or search. */
export const Empty: Story = {
  decorators: [
    withStore({
      groupMembers: {
        ...LOADED,
        data: {
          ...FLAT,
          items_total: 0,
          members_total: 0,
          direct_members_total: 0,
        },
      },
    }),
    atLocation('/identity-groups/staff'),
  ],
};

export const Loading: Story = {
  decorators: [
    withStore({ groupMembers: LOADING }),
    atLocation('/identity-groups/staff'),
  ],
};

/**
 * A visitor who can see the group without being in it.
 *
 * A membership list is personal data about other people, so it is visible to
 * its own members and to somebody who manages users. That goes for its size
 * too. The page is still a page.
 */
export const MembershipRefused: Story = {
  decorators: [
    withStore({ groupMembers: { loaded: false, error: { status: 403 } } }),
    atLocation('/identity-groups/staff'),
  ],
};
