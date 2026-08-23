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

/** Collapsed: the providers are the point, the password is the fallback. */
export const Collapsed: Story = {};

export const Refused: Story = { args: { error: FAILED.error } };

export const Authenticating: Story = { args: { loading: true } };
