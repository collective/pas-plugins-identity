import type { Meta, StoryObj } from '@storybook/react';

import PasswordForm from './PasswordForm';
import { FAILED, withLoginCard } from '../../stories/fixtures';

const meta: Meta<typeof PasswordForm> = {
  title: 'Identity/Login/PasswordForm',
  component: PasswordForm,
  // The sentence the real page carries above this form when it is the
  // only way in, which is the case it is worth comparing against.
  decorators: [withLoginCard('Sign in with your account on this site.')],
  args: { loading: false, onSubmit: () => {} },
};
export default meta;

type Story = StoryObj<typeof PasswordForm>;

/**
 * The form on its own. Whether the login page shows it, and what it replaces
 * when it does, is `LoginForm`'s decision -- see its own stories.
 */
export const Default: Story = {};

export const Refused: Story = { args: { error: FAILED.error } };

export const Authenticating: Story = { args: { loading: true } };
