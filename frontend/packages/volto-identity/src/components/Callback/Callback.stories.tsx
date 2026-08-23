import type { Meta, StoryObj } from '@storybook/react';

import Callback from './Callback';
import { FAILED, LOADED, LOADING, withStore } from '../../stories/fixtures';

const meta: Meta<typeof Callback> = {
  title: 'Identity/Callback',
  component: Callback,
  parameters: { reactRouter: { location: '/login-identity?code=a&state=b' } },
};
export default meta;

type Story = StoryObj<typeof Callback>;

/** What the user sees for the moment the exchange takes. */
export const Working: Story = {
  decorators: [withStore({ identityCallback: LOADING, magicLinkConfirm: {} })],
};

/**
 * Every backend refusal reads the same on purpose -- expired, replayed,
 * forged and wrong-session are one message here, and the audit log carries
 * the difference.
 */
export const Refused: Story = {
  decorators: [withStore({ identityCallback: FAILED, magicLinkConfirm: {} })],
};

/**
 * The success state is a moment: the token goes into the store and the
 * browser leaves. There is nothing to look at, which is the point.
 */
export const SignedIn: Story = {
  decorators: [
    withStore({
      identityCallback: {
        ...LOADED,
        data: { token: 'a-token', came_from: '/' },
      },
      magicLinkConfirm: {},
    }),
  ],
};
