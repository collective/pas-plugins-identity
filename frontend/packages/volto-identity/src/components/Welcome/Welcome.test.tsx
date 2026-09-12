import { describe, expect, it } from 'vitest';
import React from 'react';
import { Provider } from 'react-redux';
import { render, screen } from '../../testing';

import Welcome from './Welcome';
import { GET_USER_ACCOUNT } from '../../constants/ActionTypes';
import { ALICE_ACCOUNT, LOADED, tokenFor } from '../../stories/fixtures';
import type { SignInBlockData } from '../../types';

/** `@users/alice`, as `UserProfileLoader` leaves it in the store. */
const ALICE = { id: 'alice', username: 'alice.l', fullname: 'Alice Liddell' };

const NOTHING_YET = { loading: false, loaded: false, error: null, data: null };

/**
 * Render the welcome for Alice, with a store whose state we control.
 *
 * @param data The block's settings.
 * @param state Slices to put in place of the defaults.
 * @returns Every action dispatched.
 */
function mount(data: Partial<SignInBlockData> = {}, state: any = {}) {
  const dispatched: any[] = [];
  // Built once, as a store holds it. A `getState` that spreads a fresh slice
  // on every call hands `useSelector` a new snapshot each render, and React
  // re-renders until it gives up.
  const snapshot = {
    userSession: { token: tokenFor('alice') },
    userProfile: { ...LOADED, data: ALICE },
    userAccount: { ...LOADED, data: ALICE_ACCOUNT },
    ...state,
  };
  const store = {
    getState: () => snapshot,
    subscribe: () => () => {},
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
  };
  render(
    <Provider store={store as any}>
      <Welcome data={{ '@type': 'identitySignIn', ...data }} />
    </Provider>,
  );
  return dispatched;
}

/**
 * Read the summary as the pairs it shows.
 *
 * @returns Each term with its description.
 */
function summary(): Record<string, string> {
  const terms = Array.from(document.querySelectorAll('dt'));
  return Object.fromEntries(
    terms.map((dt) => [dt.textContent, dt.nextElementSibling?.textContent]),
  );
}

describe('Welcome', () => {
  it('asks for the account with enough events to find two sign-ins', () => {
    const dispatched = mount({}, { userAccount: NOTHING_YET });

    expect(dispatched).toEqual([
      {
        type: GET_USER_ACCOUNT,
        request: { op: 'get', path: '/@user-account/alice?events=100' },
      },
    ]);
  });

  it('asks nothing when the answer is already here', () => {
    expect(mount()).toEqual([]);
  });

  it('does not take an answer about somebody else for this user', () => {
    // The account page fills the same slice with whoever an administrator
    // last looked at.
    const dispatched = mount(
      {},
      { userAccount: { ...LOADED, data: { ...ALICE_ACCOUNT, userid: 'bob' } } },
    );

    expect(dispatched.map((action) => action.type)).toEqual([GET_USER_ACCOUNT]);
    expect(summary()).toEqual({});
  });

  it('asks nothing when every line is switched off', () => {
    const dispatched = mount(
      {
        showProfile: false,
        showEmail: false,
        showProvider: false,
        showLastLogin: false,
      },
      { userAccount: NOTHING_YET },
    );

    expect(dispatched).toEqual([]);
    expect(screen.getByText('Hello Alice Liddell!')).toBeTruthy();
  });

  it('fills in the welcome message', () => {
    mount({ greeting: '{username} is {fullname}' });

    expect(screen.getByText('alice.l is Alice Liddell')).toBeTruthy();
  });

  it('says hello with the default when nobody wrote a message', () => {
    mount();

    expect(screen.getByText('Hello Alice Liddell!')).toBeTruthy();
  });

  it('falls back to the userid before the user is loaded', () => {
    mount({ greeting: '{username}' }, { userProfile: NOTHING_YET });

    expect(screen.getByText('alice')).toBeTruthy();
  });

  it('names what they signed in with, and when they did before', () => {
    // The newest sign-in is this one; the one before it is the last login.
    // The link between them is an event of another kind, and is skipped.
    mount();

    expect(summary()['Authenticated with']).toBe('GitHub');
    expect(summary()['Last login']).toContain('September 10, 2026');
  });

  it('links to their profile inside the site', () => {
    mount();

    expect(
      screen.getByRole('link', { name: 'Alice Liddell' }).getAttribute('href'),
    ).toBe('/identity-profiles/alice');
  });

  it('shows the address that stands for them', () => {
    // Not the first address: the preferred one.
    mount();

    expect(summary()['Preferred email']).toBe('alice@example.com (verified)');
  });

  it('leaves out the lines switched off', () => {
    mount({ showProvider: false, showLastLogin: false });

    expect(Object.keys(summary())).toEqual(['Your profile', 'Preferred email']);
  });
});
