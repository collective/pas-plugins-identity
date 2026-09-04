import type { Meta, StoryObj } from '@storybook/react';
import { MemoryRouter, Route } from 'react-router-dom';
import React from 'react';

import UserAccount from './UserAccount';
import { USER_ACCOUNT_PATH } from '../../config/routes';
import {
  FAILED,
  LOADED,
  USER_ACCOUNT,
  withStore,
} from '../../stories/fixtures';

/**
 * The page a Manager reaches from the users control panel.
 *
 * Rendered at its own route rather than mounted bare: the page reads the
 * userid off the path, which is the whole reason it is a route and not the
 * modal it used to be.
 */
const atRoute = (Story: () => React.ReactNode) => (
  <MemoryRouter initialEntries={['/controlpanel/users/erico/account']}>
    <Route path={USER_ACCOUNT_PATH} render={() => <>{Story()}</>} />
  </MemoryRouter>
);

const meta: Meta<typeof UserAccount> = {
  title: 'Identity/ControlPanel/UserAccount',
  component: UserAccount,
  decorators: [atRoute],
};
export default meta;

type Story = StoryObj<typeof UserAccount>;

export const Default: Story = {
  decorators: [withStore({ userAccount: { ...LOADED, data: USER_ACCOUNT } })],
};

export const Loading: Story = {
  decorators: [
    withStore({
      userAccount: { loading: true, loaded: false, error: null, data: null },
    }),
  ],
};

/**
 * Arrived from another user's page, before this one's answer is in.
 *
 * One slice in the store holds one account, so the previous user is still in
 * it -- and rendering their identities under this person's name is the one
 * mistake this page must not make.
 */
export const AnotherUserStillInTheStore: Story = {
  decorators: [
    withStore({
      userAccount: {
        ...LOADED,
        data: { ...USER_ACCOUNT, userid: 'somebody-else' },
      },
    }),
  ],
};

/** A Manager without the permission, or a userid that is not there. */
export const Refused: Story = {
  decorators: [withStore({ userAccount: { ...FAILED, data: null } })],
};
