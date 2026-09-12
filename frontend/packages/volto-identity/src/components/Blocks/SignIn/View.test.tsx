import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { Provider } from 'react-redux';
import { fireEvent, render, screen } from '../../../testing';

import View from './View';
import { START_PROVIDER_LOGIN } from '../../../constants/ActionTypes';
import * as showPloneLoginModule from '../../../helpers/showPloneLogin';
import {
  ALICE_ACCOUNT,
  GITHUB,
  GOOGLE,
  LOADED,
  tokenFor,
} from '../../../stories/fixtures';
import type { LoginProvider } from '../../../types';

/**
 * Whether `useClient` says this is the browser.
 *
 * On the server it says no, and that render is the one a cache keeps.
 */
const { client } = vi.hoisted(() => ({ client: { value: true } }));

vi.mock('@plone/volto/hooks/client/useClient', () => ({
  useClient: () => client.value,
}));

interface Mount {
  token?: string;
  providers?: LoginProvider[];
  isEditMode?: boolean;
  previewAnonymous?: boolean;
}

/**
 * Render the block on `/news`, with a store whose state we control.
 *
 * @param options Who is looking, and at what.
 * @returns Every action dispatched.
 */
function mount({
  token,
  providers = [GITHUB, GOOGLE],
  isEditMode,
  previewAnonymous,
}: Mount = {}) {
  const dispatched: any[] = [];
  const state = {
    loginProviders: { ...LOADED, data: providers },
    providerLogin: {},
    magicLinkSend: {},
    userSession: { token, login: {} },
    userProfile: {
      ...LOADED,
      data: { id: 'alice', username: 'alice', fullname: 'Alice Liddell' },
    },
    userAccount: { ...LOADED, data: ALICE_ACCOUNT },
  };
  const store = {
    getState: () => state,
    subscribe: () => () => {},
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
  };
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={['/news']}>
        <View
          data={{ '@type': 'identitySignIn', previewAnonymous }}
          isEditMode={isEditMode}
        />
      </MemoryRouter>
    </Provider>,
  );
  return dispatched;
}

/**
 * The provider sign-ins the block started, by the path each asked for.
 *
 * @param dispatched Every action dispatched.
 * @returns The request paths.
 */
function starts(dispatched: any[]): string[] {
  return dispatched
    .filter((action) => action.type === START_PROVIDER_LOGIN)
    .map((action) => action.request.path);
}

describe('View', () => {
  beforeEach(() => {
    vi.spyOn(showPloneLoginModule, 'showPloneLogin').mockReturnValue(false);
  });

  afterEach(() => {
    client.value = true;
    vi.restoreAllMocks();
  });

  it('offers a visitor the ways in', () => {
    mount();

    expect(screen.getByRole('button', { name: /GitHub/ })).toBeTruthy();
    expect(screen.getByRole('button', { name: /Google/ })).toBeTruthy();
  });

  it('shows them in the login card, heading and description included', () => {
    // The card `/login` draws, and not the page: a block has no business
    // setting the page's title or claiming its id.
    mount();

    const card = document.querySelector(
      '.identity-sign-in .identity-login-card',
    );
    expect(card?.querySelector('.title')?.textContent).toBe('Log in');
    expect(card?.querySelector('.description')?.textContent).toBe(
      'Choose how you would like to sign in.',
    );
    expect(card?.querySelector('.form button')).toBeTruthy();
    expect(document.querySelector('#page-login')).toBeNull();
  });

  it('brings a visitor back to this page after signing in', () => {
    const dispatched = mount();

    fireEvent.click(screen.getByRole('button', { name: /GitHub/ }));

    expect(starts(dispatched)).toEqual([
      '/@login-providers/github?came_from=%2Fnews',
    ]);
  });

  it('never goes straight to a sole provider', () => {
    // Somebody on `/login` asked to sign in. Somebody on a page with this
    // block came for the page.
    const dispatched = mount({ providers: [GITHUB] });

    expect(starts(dispatched)).toEqual([]);
    expect(screen.getByRole('button', { name: /GitHub/ })).toBeTruthy();
  });

  it('greets somebody signed in, and offers them no way in', () => {
    mount({ token: tokenFor('alice') });

    expect(screen.getByText('Hello Alice Liddell!')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /GitHub/ })).toBeNull();
  });

  it('renders neither until it is in the browser', () => {
    // The server's render is what a cache in front of the site keeps, so it
    // must not hold anybody's welcome -- and holds nobody's sign-in options
    // either, which would flash for somebody signed in.
    client.value = false;

    const dispatched = mount({ token: tokenFor('alice') });

    expect(
      document.querySelector('.identity-sign-in')?.childNodes,
    ).toHaveLength(0);
    expect(dispatched).toEqual([]);
  });

  it('shows an editor the ways in when asked to preview', () => {
    const dispatched = mount({
      token: tokenFor('alice'),
      isEditMode: true,
      previewAnonymous: true,
    });

    fireEvent.click(screen.getByRole('button', { name: /GitHub/ }));

    // A preview: pressing a button starts nothing.
    expect(starts(dispatched)).toEqual([]);
    expect(screen.queryByText('Hello Alice Liddell!')).toBeNull();
  });

  it('keeps the welcome outside the editor, whatever the switch says', () => {
    mount({ token: tokenFor('alice'), previewAnonymous: true });

    expect(screen.getByText('Hello Alice Liddell!')).toBeTruthy();
  });
});
