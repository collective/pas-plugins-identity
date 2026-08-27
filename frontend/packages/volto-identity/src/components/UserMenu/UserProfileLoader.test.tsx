import { describe, expect, it, vi } from 'vitest';
import { render } from '../../testing';
import { Provider } from 'react-redux';
import React from 'react';

import UserProfileLoader from './UserProfileLoader';

/** A JWT-shaped token whose payload names `sub`. */
function tokenFor(sub: string): string {
  const body = Buffer.from(JSON.stringify({ sub, exp: 9e9 }))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `header.${body}.signature`;
}

function renderLoader(state: Record<string, unknown>) {
  const dispatch = vi.fn((action: unknown) => action);
  const store = {
    getState: () => state,
    dispatch,
    subscribe: () => () => {},
  };
  render(
    <Provider store={store as never}>
      <UserProfileLoader />
    </Provider>,
  );
  return dispatch;
}

const EMPTY = { loading: false, loaded: false, error: null, data: null };

describe('UserProfileLoader', () => {
  it('asks for the signed-in user', () => {
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: EMPTY,
    });

    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        request: { op: 'get', path: '/@users/alice' },
      }),
    );
  });

  it('asks for nothing when nobody is signed in', () => {
    const dispatch = renderLoader({
      userSession: { token: '' },
      userProfile: EMPTY,
    });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not ask again for a user it already holds', () => {
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: {
        loading: false,
        loaded: true,
        error: null,
        data: { id: 'alice' },
      },
    });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not ask while a request is in flight', () => {
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: { ...EMPTY, loading: true },
    });

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('asks again when a different user signs in', () => {
    const dispatch = renderLoader({
      userSession: { token: tokenFor('bob') },
      userProfile: {
        loading: false,
        loaded: true,
        error: null,
        data: { id: 'alice' },
      },
    });

    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        request: { op: 'get', path: '/@users/bob' },
      }),
    );
  });

  it('survives a store where nothing has been initialised yet', () => {
    // Both slices are read with optional chaining because this mounts on
    // every route, including the first render of a cold store.
    const dispatch = renderLoader({});

    expect(dispatch).not.toHaveBeenCalled();
  });

  it('does not retry forever after a failure', () => {
    // The request was refused -- 401 on a stale token, say. Retrying on
    // every render would be a request per frame.
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: {
        loading: false,
        loaded: false,
        error: { status: 401 },
        data: null,
      },
    });

    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it('does not ask again after the request failed', () => {
    // The storm, reproduced the way it actually happened: the request fails,
    // `loading` goes true then false again, and a guard made only of
    // `loading` and `loadedFor` is satisfied on the very next render. One
    // render cannot show this — the effect has to re-run, which is what the
    // oscillation below causes.
    const dispatch = vi.fn((action: unknown) => action);
    const state: Record<string, unknown> = {
      userSession: { token: tokenFor('alice') },
      userProfile: { ...EMPTY },
    };
    const store = {
      getState: () => state,
      dispatch,
      subscribe: () => () => {},
    };
    const { rerender } = render(
      <Provider store={store as never}>
        <UserProfileLoader />
      </Provider>,
    );

    // Three failed round trips' worth of state changes.
    for (const loading of [true, false, true, false, true, false]) {
      state.userProfile = loading
        ? { loading: true, loaded: false, error: null, data: null }
        : { loading: false, loaded: false, error: { status: 401 }, data: null };
      rerender(
        <Provider store={{ ...store, getState: () => state } as never}>
          <UserProfileLoader />
        </Provider>,
      );
    }

    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it('does not ask again after a failure it already saw', () => {
    // The storm. A failed request leaves `loadedFor` unset and `loading`
    // false, so a guard made only of those two is satisfied on the very next
    // render and the effect fires again — for ever. A token that no longer
    // authenticates but still decodes to a userid, which is exactly what a
    // stale token against a rebuilt site is, produced about 150 requests a
    // second against `@users/<id>` in the demo until the tab was closed.
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: {
        loading: false,
        loaded: false,
        error: { status: 401 },
        data: null,
      },
    });

    expect(dispatch).toHaveBeenCalledTimes(1);
  });

  it('asks again when the user changes', () => {
    // One attempt per userid, not one attempt ever: signing in as somebody
    // else has to fetch somebody else.
    const dispatch = renderLoader({
      userSession: { token: tokenFor('alice') },
      userProfile: {
        loading: false,
        loaded: false,
        error: { status: 401 },
        data: null,
      },
    });
    const first = dispatch.mock.calls.length;

    const second = renderLoader({
      userSession: { token: tokenFor('bob') },
      userProfile: {
        loading: false,
        loaded: false,
        error: { status: 401 },
        data: null,
      },
    });

    expect(first).toBe(1);
    expect(second).toHaveBeenCalledWith(
      expect.objectContaining({
        request: { op: 'get', path: '/@users/bob' },
      }),
    );
  });
});
