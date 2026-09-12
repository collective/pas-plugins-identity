import type { Meta, StoryObj } from '@storybook/react';

import View from './View';
import {
  ALICE_ACCOUNT,
  LOADED,
  PROVIDERS,
  tokenFor,
  withStore,
} from '../../../stories/fixtures';

/** What the ways in read, for somebody not signed in. */
const VISITOR = {
  loginProviders: { ...LOADED, data: PROVIDERS },
  providerLogin: {},
  magicLinkSend: {},
  userSession: { token: null, login: {} },
};

const meta: Meta<typeof View> = {
  title: 'Identity/Blocks/SignIn/View',
  component: View,
  args: { data: { '@type': 'identitySignIn' } },
};
export default meta;

type Story = StoryObj<typeof View>;

/** The sign-in options `/login` offers, without the page around them. */
export const ForAVisitor: Story = { decorators: [withStore(VISITOR)] };

/** The same block, for somebody signed in. */
export const ForSomebodySignedIn: Story = {
  decorators: [
    withStore({
      ...VISITOR,
      userSession: { token: tokenFor('alice'), login: {} },
      userProfile: {
        ...LOADED,
        data: { id: 'alice', username: 'alice', fullname: 'Alice Liddell' },
      },
      userAccount: { ...LOADED, data: ALICE_ACCOUNT },
    }),
  ],
};
