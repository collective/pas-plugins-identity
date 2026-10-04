import type { Meta, StoryObj } from '@storybook/react';

import CompleteProfileCard from './CompleteProfileCard';

const meta: Meta<typeof CompleteProfileCard> = {
  title: 'Identity/CompleteProfile/CompleteProfileCard',
  component: CompleteProfileCard,
  args: {
    held: true,
    missing: ['Organisation', 'Country'],
    editHref: '/@@edit/identity-profiles/erico',
  },
};
export default meta;

type Story = StoryObj<typeof CompleteProfileCard>;

/** The backend named the missing fields. */
export const MissingFields: Story = {};

/** It did not. */
export const Unnamed: Story = { args: { missing: [] } };

/** Nothing is missing any more. */
export const Complete: Story = { args: { held: false, editHref: null } };
