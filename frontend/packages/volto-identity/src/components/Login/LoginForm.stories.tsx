import type { Meta, StoryObj } from '@storybook/react';

import LoginForm from './LoginForm';
import {
  EMAIL,
  FAILED,
  PROVIDERS,
  withLoginCard,
} from '../../stories/fixtures';

const meta: Meta<typeof LoginForm> = {
  title: 'Identity/Login/LoginForm',
  component: LoginForm,
  decorators: [withLoginCard()],
  args: {
    providers: PROVIDERS,
    loading: false,
    starting: false,
    magicLinkSent: false,
    magicLinkLoading: false,
    passwordLoading: false,
    showPloneLogin: true,
    onSelectProvider: () => {},
    onSendMagicLink: () => {},
    onPasswordLogin: () => {},
  },
};
export default meta;

type Story = StoryObj<typeof LoginForm>;

export const Providers: Story = {};

/**
 * Email as one of the buttons.
 *
 * It is not a redirect, so pressing it opens its field on the next step
 * rather than leaving this origin -- but on the picker it is a way in like
 * any other, which is the only thing the picker is about.
 */
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

/** A site that has providers and wants no password beside them. */
export const ProvidersOnly: Story = {
  args: { showPloneLogin: false },
};

/**
 * One provider and nothing else: the picker is skipped and the flow starts
 * on its own, so what is on screen is where it is going.
 */
export const TheOnlyWayIn: Story = {
  args: { showPloneLogin: false, providers: [PROVIDERS[0]] },
};

/** The same site, after that provider turned out to be unreachable. */
export const TheOnlyWayInFailed: Story = {
  args: {
    showPloneLogin: false,
    providers: [PROVIDERS[0]],
    error: FAILED.error,
  },
};

/**
 * A site whose only way in is a link in the post.
 *
 * Also what the Email button opens on a site with a choice: one way in is
 * not a choice, so the step it would lead to is the page itself. The step
 * reached by pressing the button is an interaction rather than a state, so
 * it is pinned in `LoginForm.test.tsx` rather than here.
 */
export const MagicLinkOnly: Story = {
  args: { showPloneLogin: false, providers: [EMAIL] },
};

export const Redirecting: Story = { args: { starting: true } };

export const StartFailed: Story = { args: { error: FAILED.error } };

/**
 * A refused password, on the page that shows it.
 *
 * `passwordError` reaches `PasswordForm`, and that form is only on screen
 * once it has been opened -- so with providers configured this story rendered
 * the picker and showed nothing at all. A site with no providers *is* the
 * password form, which is the state worth looking at.
 */
export const PasswordRefused: Story = {
  args: { providers: [], passwordError: FAILED.error },
};

/** The same form while the attempt is still in flight. */
export const Authenticating: Story = {
  args: { providers: [], passwordLoading: true },
};

/** A refusal from the provider listing, over the options it could not load. */
export const StartFailedDismissible: Story = {
  args: { error: FAILED.error },
};
