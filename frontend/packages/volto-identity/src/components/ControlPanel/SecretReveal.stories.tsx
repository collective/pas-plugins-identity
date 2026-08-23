import type { Meta, StoryObj } from '@storybook/react';

import SecretReveal from './SecretReveal';
import { CLIENT, MINTED_CLIENT } from '../../stories/fixtures';

const meta: Meta<typeof SecretReveal> = {
  title: 'Identity/ControlPanel/SecretReveal',
  component: SecretReveal,
  args: { client: MINTED_CLIENT, onDismiss: () => {} },
};
export default meta;

type Story = StoryObj<typeof SecretReveal>;

/**
 * The one moment the secret exists in a form anybody can read. The server
 * keeps a hash, so this is not recoverable and nearly the whole design of the
 * clients panel is about this appearing exactly once.
 */
export const JustMinted: Story = {};

/** A rotation says the same thing about a secret that already existed. */
export const Rotated: Story = {
  args: {
    client: {
      ...MINTED_CLIENT,
      notice: 'The previous secret stopped working the moment this was minted.',
    },
  },
};

/** Without a secret there is nothing to reveal. */
export const NothingToShow: Story = { args: { client: CLIENT } };
