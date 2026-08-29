import type { Meta, StoryObj } from '@storybook/react';

import FirstLogin from './FirstLogin';
import { LOADED, LOADING, withStore } from '../../stories/fixtures';

const meta: Meta<typeof FirstLogin> = {
  title: 'Identity/FirstLogin',
  component: FirstLogin,
};
export default meta;

type Story = StoryObj<typeof FirstLogin>;

export const Deciding: Story = {
  decorators: [withStore({ myProfile: LOADING })],
};

/** A user whose Profile still needs filling in. */
export const ProfileIncomplete: Story = {
  decorators: [
    withStore({
      myProfile: {
        ...LOADED,
        data: {
          '@id': '/@my-profile',
          userid: 'alice',
          profile: 'https://example.org/identity-profiles/alice',
          review_state: 'incomplete',
        },
      },
    }),
  ],
};

/** A user with no Profile: there is nothing to complete. */
export const NoProfile: Story = {
  decorators: [
    withStore({
      myProfile: {
        ...LOADED,
        data: {
          '@id': '/@my-profile',
          userid: 'alice',
          profile: null,
          review_state: null,
        },
      },
    }),
  ],
};
