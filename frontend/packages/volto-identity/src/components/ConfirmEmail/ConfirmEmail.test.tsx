/**
 * The address confirmation page, mounted.
 *
 * What it offers is the part that has to be right: only verified addresses,
 * because the backend refuses anything else, and the one already standing for
 * the user chosen to begin with, so confirming without changing anything is a
 * single click.
 */
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { IntlProvider } from '../../testing';

import ConfirmEmail from './ConfirmEmail';
import { CONFIRM_EMAIL, GET_MY_PROFILE } from '../../constants/ActionTypes';

const IDLE = { loading: false, loaded: false, error: null, data: null };
const LOADED = { loading: false, loaded: true, error: null };

const ASKING = {
  '@id': '/@my-profile',
  userid: 'alice',
  profile: 'https://example.org/identity-profiles/alice',
  review_state: 'incomplete',
  missing: [],
  confirm_email: true,
  emails: [
    { address: 'alice@example.com', verified: true, preferred: true },
    { address: 'alice@example.org', verified: true, preferred: false },
    { address: 'alice@example.net', verified: false, preferred: false },
  ],
};

function mount(state: any) {
  const dispatched: any[] = [];
  const store = {
    getState: () => ({
      userSession: { token: 'a-token' },
      emailConfirmation: IDLE,
      ...state,
    }),
    subscribe: () => () => {},
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
  };
  render(
    <Provider store={store as any}>
      <IntlProvider locale="en">
        <MemoryRouter initialEntries={['/confirm-email']}>
          <ConfirmEmail />
        </MemoryRouter>
      </IntlProvider>
    </Provider>,
  );
  return dispatched;
}

function choices(): HTMLInputElement[] {
  return Array.from(document.querySelectorAll('input[type="radio"]'));
}

describe('ConfirmEmail', () => {
  it('asks for the profile when nobody has', () => {
    const dispatched = mount({ myProfile: IDLE });

    expect(dispatched.map((action) => action.type)).toEqual([GET_MY_PROFILE]);
  });

  it('asks nothing when the answer is already here', () => {
    // `ProfileGate` asked on the way in.
    expect(mount({ myProfile: { ...LOADED, data: ASKING } })).toHaveLength(0);
  });

  it('asks nothing while anonymous', () => {
    expect(mount({ userSession: {}, myProfile: IDLE })).toHaveLength(0);
  });

  it('offers only the verified addresses', () => {
    mount({ myProfile: { ...LOADED, data: ASKING } });

    expect(choices().map((input) => input.value)).toEqual([
      'alice@example.com',
      'alice@example.org',
    ]);
  });

  it('starts from the address already standing for the user', () => {
    // Second in the list here, so starting from the first offered would not
    // pass for the right reason.
    mount({
      myProfile: {
        ...LOADED,
        data: {
          ...ASKING,
          emails: [
            { address: 'alice@example.com', verified: true, preferred: false },
            { address: 'alice@example.org', verified: true, preferred: true },
          ],
        },
      },
    });

    expect(choices().find((input) => input.checked)?.value).toBe(
      'alice@example.org',
    );
  });

  it('confirms the address chosen', () => {
    const dispatched = mount({ myProfile: { ...LOADED, data: ASKING } });

    fireEvent.click(choices()[1]);
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));

    const sent = dispatched.find((action) => action.type === CONFIRM_EMAIL);
    expect(sent?.request.data).toEqual({ email: 'alice@example.org' });
  });

  it('cannot be sent twice while the first answer is on its way', () => {
    mount({
      myProfile: { ...LOADED, data: ASKING },
      emailConfirmation: { ...IDLE, loading: true },
    });

    expect(
      (screen.getByRole('button', { name: 'Confirm' }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });

  it('says when the backend refused the answer', () => {
    mount({
      myProfile: { ...LOADED, data: ASKING },
      emailConfirmation: { ...IDLE, error: { status: 400 } },
    });

    expect(screen.getByRole('alert')).not.toBeNull();
  });

  it('says which address it recorded', () => {
    const answered = {
      ...ASKING,
      review_state: 'complete',
      confirm_email: false,
      emails: [
        { address: 'alice@example.org', verified: true, preferred: true },
        { address: 'alice@example.com', verified: true, preferred: false },
      ],
    };

    mount({
      myProfile: { ...LOADED, data: answered },
      emailConfirmation: { ...LOADED, data: answered },
    });

    expect(screen.getByRole('status').textContent).toContain(
      'alice@example.org',
    );
  });

  it('says when there is nothing to confirm', () => {
    // Somebody who opened the page directly, or a site that stopped asking.
    mount({
      myProfile: { ...LOADED, data: { ...ASKING, confirm_email: false } },
    });

    expect(choices()).toHaveLength(0);
    expect(screen.getByRole('status')).not.toBeNull();
  });
});
