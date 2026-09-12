import type { Meta, StoryObj } from '@storybook/react';

import ConfirmEmail from './ConfirmEmail';
import { LOADED, LOADING, withStore } from '../../stories/fixtures';

const meta: Meta<typeof ConfirmEmail> = {
  title: 'Identity/ConfirmEmail',
  component: ConfirmEmail,
};
export default meta;

type Story = StoryObj<typeof ConfirmEmail>;

const SIGNED_IN = { userSession: { token: 'a-token' } };
const IDLE = { loading: false, loaded: false, error: null, data: null };

/** Two verified addresses and one the site has not proved. */
const ASKING = {
  '@id': '/@my-profile',
  userid: 'alice',
  profile: 'https://example.org/identity-profiles/alice',
  review_state: 'incomplete',
  missing: [],
  confirm_email: true,
  emails: [
    { address: 'alice@example.com', verified: true, preferred: true },
    { address: 'alice@example.org', verified: true, preferred: false },
    { address: 'alice@example.net', verified: false, preferred: false },
  ],
};

const ANSWERED = {
  ...ASKING,
  review_state: 'complete',
  confirm_email: false,
  emails: [
    { address: 'alice@example.org', verified: true, preferred: true },
    { address: 'alice@example.com', verified: true, preferred: false },
    { address: 'alice@example.net', verified: false, preferred: false },
  ],
};

export const Loading: Story = {
  decorators: [
    withStore({ ...SIGNED_IN, myProfile: LOADING, emailConfirmation: IDLE }),
  ],
};

/** The question: only the verified addresses are offered. */
export const Asking: Story = {
  decorators: [
    withStore({
      ...SIGNED_IN,
      myProfile: { ...LOADED, data: ASKING },
      emailConfirmation: IDLE,
    }),
  ],
};

/** The answer is on its way, so it cannot be sent again. */
export const Confirming: Story = {
  decorators: [
    withStore({
      ...SIGNED_IN,
      myProfile: { ...LOADED, data: ASKING },
      emailConfirmation: LOADING,
    }),
  ],
};

/** The backend refused the answer. */
export const Refused: Story = {
  decorators: [
    withStore({
      ...SIGNED_IN,
      myProfile: { ...LOADED, data: ASKING },
      emailConfirmation: { ...IDLE, error: { status: 400 } },
    }),
  ],
};

/** Answered, on a site that does not mount the gate to send the user on. */
export const Confirmed: Story = {
  decorators: [
    withStore({
      ...SIGNED_IN,
      myProfile: { ...LOADED, data: ANSWERED },
      emailConfirmation: { ...LOADED, data: ANSWERED },
    }),
  ],
};

/** Opened directly by somebody nobody is asking. */
export const NothingToConfirm: Story = {
  decorators: [
    withStore({
      ...SIGNED_IN,
      myProfile: { ...LOADED, data: ANSWERED },
      emailConfirmation: IDLE,
    }),
  ],
};
