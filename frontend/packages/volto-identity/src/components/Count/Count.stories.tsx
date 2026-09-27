import type { Meta, StoryObj } from '@storybook/react';

import Count from './Count';

const meta: Meta<typeof Count> = {
  title: 'Identity/Count',
  component: Count,
  args: { value: 42, label: 'members' },
};
export default meta;

type Story = StoryObj<typeof Count>;

export const Primary: Story = {};

/** Quieter, for a figure that qualifies another beside it. */
export const Secondary: Story = {
  args: { value: 12, label: 'directly', secondary: true },
};

/** Formatted for the reader's locale. */
export const Large: Story = {
  args: { value: 12345, label: 'members' },
};
