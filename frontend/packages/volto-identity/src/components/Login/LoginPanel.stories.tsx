import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import LoginPanel from './LoginPanel';

const meta: Meta<typeof LoginPanel> = {
  title: 'Identity/Login/LoginPanel',
  component: LoginPanel,
  args: {
    title: 'Log in',
    description: 'Choose how you would like to sign in.',
    children: (
      // Centred and padded, so the story shows the card's body as the page
      // fills it rather than a line of text against its top-left corner.
      <p
        style={{
          display: 'flex',
          height: '100%',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 'var(--identity-gap)',
          margin: 0,
          textAlign: 'center',
        }}
      >
        The sign-in options go here.
      </p>
    ),
  },
};
export default meta;

type Story = StoryObj<typeof LoginPanel>;

/** The chrome, which is volto-authomatic's so the two add-ons match. */
export const Default: Story = {};

export const NoProvidersConfigured: Story = {
  args: { description: 'Sign in with your account on this site.' },
};
