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
