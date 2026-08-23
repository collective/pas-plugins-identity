import type { Meta, StoryObj } from '@storybook/react';

import LoginForm from './LoginForm';
import { EMAIL, FAILED, PROVIDERS } from '../../stories/fixtures';

const meta: Meta<typeof LoginForm> = {
  title: 'Identity/Login/LoginForm',
  component: LoginForm,
  args: {
    providers: PROVIDERS,
    loading: false,
    starting: false,
    magicLinkSent: false,
    magicLinkLoading: false,
    passwordLoading: false,
    onSelectProvider: () => {},
    onSendMagicLink: () => {},
    onPasswordLogin: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof LoginForm>;

export const Providers: Story = {};

/** The magic link is a form rather than a redirect, so it gets no button. */
export const WithMagicLink: Story = {
  args: { providers: [...PROVIDERS, EMAIL] },
};

export const Loading: Story = { args: { loading: true } };

/**
 * A site can legitimately have none configured, and an authorization server
 * never will: its users are local. The password has to be offered here, or
 * there is no way in at all.
 */
export const NoProviders: Story = { args: { providers: [] } };

export const Redirecting: Story = { args: { starting: true } };

export const StartFailed: Story = { args: { error: FAILED.error } };

export const PasswordRefused: Story = { args: { passwordError: FAILED.error } };
