import type { Meta, StoryObj } from '@storybook/react';

import ProfileEmails from './ProfileEmails';
import { PROFILE_EMAILS } from '../../stories/fixtures';

const meta: Meta<typeof ProfileEmails> = {
  title: 'Identity/Identities/ProfileEmails',
  component: ProfileEmails,
  args: {
    emails: PROFILE_EMAILS,
    profileUrl: '/identity-profiles/erico',
    loading: false,
    busy: false,
    sent: false,
    onVerify: () => {},
    onPrefer: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ProfileEmails>;

/** One address proved, one still to prove. */
export const Several: Story = {};

/** Nothing verified yet, which is how a profile arrives from a provider. */
export const NoneVerified: Story = {
  args: {
    emails: PROFILE_EMAILS.map((entry) => ({ ...entry, verified: false })),
  },
};

/**
 * No addresses at all.
 *
 * There is nothing to verify and no box to type one into: an address is added
 * on the profile, and this points at it.
 */
export const Empty: Story = { args: { emails: [] } };

/** A confirmation link has gone out. Nothing is verified until it is clicked,
 * which may well happen in another browser entirely. */
export const Sent: Story = { args: { sent: true } };

/** While a send is in flight, nothing else may be started. */
export const Busy: Story = { args: { busy: true } };

/**
 * A page that only shows the addresses.
 *
 * Without a handler the buttons are not rendered at all, rather than rendered
 * inert: an action that does nothing when clicked is worse than one that was
 * never offered.
 */
export const NoReordering: Story = { args: { onPrefer: undefined } };

/**
 * One address, so there is nothing to choose between.
 *
 * The hint above the list is what disappears; the address is preferred by
 * being the only one.
 */
export const OnlyOne: Story = { args: { emails: PROFILE_EMAILS.slice(0, 1) } };
