import React from 'react';
import type { ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react';

import MemberRow from './MemberRow';

const meta: Meta<typeof MemberRow> = {
  title: 'Identity/Views/GroupsView/MemberRow',
  component: MemberRow,
  args: {
    groupId: 'staff',
    member: {
      '@id': '/identity-profiles/charlie',
      id: 'charlie',
      fullname: 'Charlie Bucket',
      login: 'charlie@example.com',
      profile_url: '/identity-profiles/charlie',
      through: ['staff'],
    },
  },
  // A row is a list item, and only renders as one inside a list.
  decorators: [
    (Story: () => ReactNode) => (
      <ul style={{ listStyle: 'none' }}>{Story()}</ul>
    ),
  ],
};
export default meta;

type Story = StoryObj<typeof MemberRow>;

/** In the group itself. */
export const Direct: Story = {};

/** In the group through a nested one, and saying so. */
export const Inherited: Story = {
  args: {
    member: {
      '@id': '/identity-profiles/alice',
      id: 'alice',
      fullname: 'Alice Liddell',
      login: 'alice@example.com',
      profile_url: '/identity-profiles/alice',
      through: ['developers', 'contractors'],
    },
  },
};

/** An account with no Profile: nowhere to send the reader. */
export const WithoutAProfile: Story = {
  args: {
    member: {
      '@id': '/@group-members/staff/emilia',
      id: 'emilia',
      fullname: 'Emilia Galotti',
      login: 'emilia@example.com',
      profile_url: null,
      through: ['staff'],
    },
  },
};
