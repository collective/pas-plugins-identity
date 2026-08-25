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
});
