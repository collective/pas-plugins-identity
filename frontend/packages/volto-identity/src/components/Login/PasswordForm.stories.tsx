import type { Meta, StoryObj } from '@storybook/react';

import PasswordForm from './PasswordForm';
import { FAILED } from '../../stories/fixtures';

const meta: Meta<typeof PasswordForm> = {
  title: 'Identity/Login/PasswordForm',
  component: PasswordForm,
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
