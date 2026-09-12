import type { Meta, StoryObj } from '@storybook/react';

import Welcome from './Welcome';
import {
  ALICE_ACCOUNT,
  LOADED,
  LOADING,
  tokenFor,
  withStore,
} from '../../stories/fixtures';

/** A signed-in Alice, with everything the welcome reads already loaded. */
const SIGNED_IN = {
  userSession: { token: tokenFor('alice') },
  userProfile: {
    ...LOADED,
    data: { id: 'alice', username: 'alice', fullname: 'Alice Liddell' },
  },
  userAccount: { ...LOADED, data: ALICE_ACCOUNT },
};

const meta: Meta<typeof Welcome> = {
  title: 'Identity/Welcome/Welcome',
  component: Welcome,
  args: { data: { '@type': 'identitySignIn' } },
};
export default meta;

type Story = StoryObj<typeof Welcome>;

/** A new block: the default message, and every line. */
export const Default: Story = { decorators: [withStore(SIGNED_IN)] };

/** A message an editor wrote, with both placeholders. */
export const OwnMessage: Story = {
  args: {
    data: {
      '@type': 'identitySignIn',
      greeting: 'Welcome back, {fullname} ({username}).',
    },
  },
  decorators: [withStore(SIGNED_IN)],
};

/** Every summary line switched off. */
export const GreetingOnly: Story = {
  args: {
    data: {
      '@type': 'identitySignIn',
      showProfile: false,
      showEmail: false,
      showProvider: false,
      showLastLogin: false,
    },
  },
  decorators: [withStore(SIGNED_IN)],
};

/**
 * Before `@user-account` has answered.
 *
 * The greeting needs only the user, so it is there; the summary waits.
 */
export const WaitingForTheAccount: Story = {
  decorators: [withStore({ ...SIGNED_IN, userAccount: LOADING })],
};
