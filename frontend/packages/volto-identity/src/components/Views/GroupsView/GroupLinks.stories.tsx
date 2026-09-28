import type { Meta, StoryObj } from '@storybook/react';

import GroupLinks from './GroupLinks';

const meta: Meta<typeof GroupLinks> = {
  title: 'Identity/Views/GroupsView/GroupLinks',
  component: GroupLinks,
  args: {
    title: 'Groups in this group',
    help: 'Everybody in these groups is in this one as well, at any depth.',
    groups: [
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
  },
};
export default meta;

type Story = StoryObj<typeof GroupLinks>;

/** The groups nested inside this one. */
export const Nested: Story = {};

/** The groups this one is nested inside: no help line. */
export const PartOf: Story = {
  args: {
    title: 'Part of',
    help: undefined,
    groups: [
      {
        '@id': '/@group-members/everyone',
        id: 'everyone',
        title: 'Everyone',
        group_url: '/identity-groups/everyone',
      },
    ],
  },
};

/** A stored membership of a group the site holds no page for. */
export const WithoutAPage: Story = {
  args: {
    title: 'Part of',
    help: undefined,
    groups: [
      {
        '@id': '/@group-members/legacy',
        id: 'legacy',
        title: 'legacy',
        group_url: null,
      },
    ],
  },
};
