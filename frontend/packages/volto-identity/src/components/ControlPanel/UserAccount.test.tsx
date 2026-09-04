import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '../../testing';
import { MemoryRouter, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import React from 'react';

import UserAccount from './UserAccount';
import { USER_ACCOUNT_PATH } from '../../config/routes';
import { USER_ACCOUNT } from '../../stories/fixtures';

// Chrome around the panel rather than anything this test is about, and it
// reads store slices this page does not own. `vi.mock` is hoisted above the
// imports, so it takes effect despite sitting below them.
vi.mock('@plone/volto/components/manage/Toolbar/Toolbar', () => ({
  default: () => null,
}));

function renderAt(userid: string, userAccount: any) {
  const state = { userAccount };
  const dispatched: any[] = [];
  const store = {
    getState: () => state,
    dispatch: (action: any) => {
      dispatched.push(action);
      return action;
    },
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as any}>
      <MemoryRouter initialEntries={[`/controlpanel/users/${userid}/account`]}>
        <Route path={USER_ACCOUNT_PATH} component={UserAccount} />
      </MemoryRouter>
    </Provider>,
  );
  return { dispatched };
}

const LOADED = { loading: false, loaded: true, error: null };

describe('UserAccount', () => {
  beforeEach(() => {
    const toolbar = document.createElement('div');
    toolbar.id = 'toolbar';
    document.body.appendChild(toolbar);
  });

  afterEach(() => {
    document.getElementById('toolbar')?.remove();
  });

  it('asks for the account named in the route', () => {
    // The whole point of the route: the page knows who it is about without a
    // row having fetched them first, which is what makes it linkable.
    const { dispatched } = renderAt('erico', {
      ...LOADED,
      data: USER_ACCOUNT,
    });

    const paths = dispatched
      .filter((action) => action?.request?.path)
      .map((action) => action.request.path);
    expect(paths.some((path: string) => path.includes('erico'))).toBe(true);
  });

  it('escapes the userid exactly once on the way back out', () => {
    // A userid is whatever the provider minted, and this one has to survive
    // the round trip through a path segment. react-router half decodes the
    // parameter -- `%20` becomes a space, `%2F` does not -- so handing it
    // straight to an action that escapes what it is given encodes the `%` a
    // second time and asks for a userid nobody has.
    const { dispatched } = renderAt(encodeURIComponent('a b/c'), {
      ...LOADED,
      data: null,
    });

    const paths = dispatched
      .filter((action) => action?.request?.path)
      .map((action) => action.request.path);
    expect(paths).toContain(`/@user-account/${encodeURIComponent('a b/c')}`);
    expect(paths.some((path: string) => path.includes('%25'))).toBe(false);
  });

  it('shows the account it was given', () => {
    renderAt('erico', { ...LOADED, data: USER_ACCOUNT });

    expect(screen.getByRole('tab', { name: 'Sign-in methods' })).toBeTruthy();
    expect(screen.getByText('GitHub')).toBeTruthy();
  });

  it('names the person the page is about', () => {
    renderAt('erico', { ...LOADED, data: USER_ACCOUNT });

    expect(document.body.textContent).toContain('Érico Andrei');
  });

  it('waits rather than showing the last user that was opened', () => {
    // One slice in the store holds one account. Arriving from another user's
    // page leaves their answer in it, and rendering that under this person's
    // name is the one mistake this page must not make.
    renderAt('someone-else', { ...LOADED, data: USER_ACCOUNT });

    expect(screen.queryByText('GitHub')).toBeNull();
    expect(screen.getByRole('status')).toBeTruthy();
  });

  it('reports a refusal rather than waiting for ever', () => {
    renderAt('erico', {
      loading: false,
      loaded: false,
      error: { status: 403 },
      data: null,
    });

    expect(screen.getByRole('alert')).toBeTruthy();
  });
});
