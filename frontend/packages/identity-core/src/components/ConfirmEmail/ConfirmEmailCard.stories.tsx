import type { Meta, StoryObj } from '@storybook/react';

import ConfirmEmailCard from './ConfirmEmailCard';
import { PROFILE_EMAILS } from '../../stories/fixtures';

const meta: Meta<typeof ConfirmEmailCard> = {
  title: 'Identity/ConfirmEmail/ConfirmEmailCard',
  component: ConfirmEmailCard,
  args: {
    status: 'asking',
    emails: [
      ...PROFILE_EMAILS,
      { address: 'erico@plone.social', verified: true, preferred: false },
    ],
    busy: false,
    failed: false,
    onConfirm: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof ConfirmEmailCard>;

/** Two verified addresses to choose between; the unverified one is left out. */
export const Asking: Story = {};

/** The backend refused the answer. */
export const Failed: Story = { args: { failed: true } };

/** The answer is recorded. */
export const Done: Story = {
  args: { status: 'done', recorded: 'erico@plone.org' },
};

/** Nothing is waiting to be confirmed. */
export const Nothing: Story = { args: { status: 'nothing' } };
