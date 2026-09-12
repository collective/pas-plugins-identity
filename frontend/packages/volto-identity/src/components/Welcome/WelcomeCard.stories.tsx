import type { Meta, StoryObj } from '@storybook/react';

import WelcomeCard from './WelcomeCard';

const meta: Meta<typeof WelcomeCard> = {
  title: 'Identity/Welcome/WelcomeCard',
  component: WelcomeCard,
  args: {
    greeting: 'Hello Alice Liddell!',
    profile: { to: '/identity-profiles/alice', label: 'Alice Liddell' },
    email: { address: 'alice@example.com', verified: true, preferred: true },
    provider: 'GitHub',
    lastLogin: 'September 10, 2026 at 12:00 PM',
  },
};
export default meta;

type Story = StoryObj<typeof WelcomeCard>;

/** Every line switched on, and something to say on each. */
export const Everything: Story = {};

/** A block with every summary line switched off. */
export const GreetingOnly: Story = {
  args: { profile: null, email: null, provider: null, lastLogin: null },
};

/** A welcome message an editor emptied: the card is headed "Welcome". */
export const NoGreeting: Story = { args: { greeting: '' } };

/** An address the site holds but nobody has proved. */
export const UnverifiedAddress: Story = {
  args: {
    email: { address: 'alice@example.com', verified: false, preferred: true },
  },
};

/**
 * The first sign-in the audit log holds.
 *
 * There is no sign-in before it to name, so the line is left out rather
 * than printed empty.
 */
export const FirstSignIn: Story = { args: { lastLogin: null } };
