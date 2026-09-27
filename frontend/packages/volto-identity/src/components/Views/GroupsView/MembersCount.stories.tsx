import type { Meta, StoryObj } from '@storybook/react';

import MembersCount from './MembersCount';

const meta: Meta<typeof MembersCount> = {
  title: 'Identity/Views/GroupsView/MembersCount',
  component: MembersCount,
  args: { total: 42, direct: 12 },
};
export default meta;

type Story = StoryObj<typeof MembersCount>;

/** Some of the group arrives through the groups nested inside it. */
export const Nested: Story = {};

/** Nothing nested, so everybody is a direct member and the count does not
 * split. */
export const Flat: Story = {
  args: { total: 8, direct: 8 },
};

export const One: Story = {
  args: { total: 1, direct: 1 },
};
