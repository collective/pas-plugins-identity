import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import LoginOverlay from './LoginOverlay';
import { withLoginCard } from '../../stories/fixtures';

/**
 * Something for the overlay to be over.
 *
 * The point of an overlay is what stays underneath it, so a story that showed
 * it against an empty card would not show the thing worth looking at.
 */
const Underneath = () => (
  <ul className="identity-providers">
    <li>
      <button type="button" className="identity-provider" disabled>
        <span>GitHub</span>
      </button>
    </li>
    <li>
      <button type="button" className="identity-provider" disabled>
        <span>Sign in with a password</span>
      </button>
    </li>
  </ul>
);

const meta: Meta<typeof LoginOverlay> = {
  title: 'Identity/Login/LoginOverlay',
  component: LoginOverlay,
  decorators: [
    (Story) => (
      <div className="identity-login">
        <Underneath />
        {Story()}
      </div>
    ),
    withLoginCard(),
  ],
};
export default meta;

type Story = StoryObj<typeof LoginOverlay>;

/** Waiting on the provider listing, before there is anything to choose. */
export const Loading: Story = { args: { message: 'Loading sign-in options…' } };

/** Waiting on a redirect, with the options it came from still underneath. */
export const Redirecting: Story = {
  args: { message: 'Taking you to GitHub…' },
};

/** A refusal, which the reader ends by reading it. */
export const Refused: Story = {
  args: {
    error: true,
    message: 'That sign-in option is not available right now.',
    onDismiss: () => {},
  },
};

/**
 * A refusal with nothing to go back to.
 *
 * No dismiss control, because taking it down would leave a card saying
 * nothing at all.
 */
export const RefusedWithNoWayBack: Story = {
  args: {
    error: true,
    message: 'That sign-in option is not available right now.',
  },
};
