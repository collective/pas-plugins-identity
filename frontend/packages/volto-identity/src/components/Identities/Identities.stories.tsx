import type { Meta, StoryObj } from '@storybook/react';

import Identities from './Identities';
import {
  IDENTITIES,
  LOADED,
  LOADING,
  PROFILE_EMAILS,
  PROVIDERS,
  withStore,
} from '../../stories/fixtures';

const meta: Meta<typeof Identities> = {
  title: 'Identity/Identities/Identities',
  component: Identities,
};
export default meta;

type Story = StoryObj<typeof Identities>;

const base = {
  identities: { ...LOADED, data: IDENTITIES },
  // What the page offers to add is the backend's own `available`, which is
  // not the login screen's listing: a provider taken off the login page is
  // still one an existing user may attach.
  linkableProviders: { ...LOADED, data: PROVIDERS },
  myProfile: {
    ...LOADED,
    data: {
      '@id': '/@my-profile',
      userid: 'erico',
      profile: '/identity-profiles/erico',
      review_state: 'complete',
      missing: [],
      emails: PROFILE_EMAILS,
    },
  },
  identityLinking: {},
  identityUnlink: {},
};

/** Where a signed-in user manages their own ways in. */
export const Default: Story = { decorators: [withStore(base)] };

export const Loading: Story = {
  decorators: [withStore({ ...base, identities: { ...LOADING, data: [] } })],
};

export const Unlinking: Story = {
  decorators: [withStore({ ...base, identityUnlink: LOADING })],
};
