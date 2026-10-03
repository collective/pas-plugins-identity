import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';

import LoginCard from './LoginCard';

const meta: Meta<typeof LoginCard> = {
  title: 'Identity/Login/LoginCard',
  component: LoginCard,
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

type Story = StoryObj<typeof LoginCard>;

/** The card the login page and the sign-in block both draw. */
export const Default: Story = {};

/** The callback and the first-login wait, which have nothing to describe. */
export const NoDescription: Story = { args: { description: undefined } };
