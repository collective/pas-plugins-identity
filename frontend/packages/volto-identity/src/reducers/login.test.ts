import { describe, expect, it } from 'vitest';

import {
  COMPLETE_CALLBACK,
  LIST_LOGIN_PROVIDERS,
  START_PROVIDER_LOGIN,
} from '../constants/ActionTypes';
import { identityCallback, loginProviders, providerLogin } from './login';

describe('loginProviders', () => {
  it('starts empty and not loading', () => {
    const state = loginProviders(undefined, { type: 'INIT' });

    expect(state.data).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.loaded).toBe(false);
  });

  it('keeps the items out of the listing', () => {
    const state = loginProviders(undefined, {
      type: `${LIST_LOGIN_PROVIDERS}_SUCCESS`,
      result: { '@id': 'x', items: [{ id: 'dex', driver: 'oidc-generic' }] },
    });

    expect(state.data).toHaveLength(1);
    expect(state.loaded).toBe(true);
  });

  it('survives a listing with no items', () => {
    const state = loginProviders(undefined, {
      type: `${LIST_LOGIN_PROVIDERS}_SUCCESS`,
      result: {},
    });

    expect(state.data).toEqual([]);
  });

  it('records a failure without keeping stale data', () => {
    const loaded = loginProviders(undefined, {
      type: `${LIST_LOGIN_PROVIDERS}_SUCCESS`,
      result: { items: [{ id: 'dex' }] },
    });

    const failed = loginProviders(loaded, {
      type: `${LIST_LOGIN_PROVIDERS}_FAIL`,
      error: 'boom',
    });

    expect(failed.error).toBe('boom');
    expect(failed.data).toEqual([]);
  });

  it('fills from the identities listing when it carried the component', () => {
    // How the identities page loads in one request rather than two.
    const state = loginProviders(undefined, {
      type: 'IDENTITY_LIST_IDENTITIES_SUCCESS',
      result: {
        '@components': { 'login-providers': { items: [{ id: 'dex' }] } },
      },
    });

    expect(state.data).toEqual([{ id: 'dex' }]);
    expect(state.loaded).toBe(true);
  });

  it('keeps what it has when that listing carried no component', () => {
    // The refresh after an unlink does not expand: the providers did not
    // change, and clearing them would blank the buttons for a moment.
    const loaded = loginProviders(undefined, {
      type: 'IDENTITY_LIST_LOGIN_PROVIDERS_SUCCESS',
      result: { items: [{ id: 'dex' }] },
    });

    const after = loginProviders(loaded, {
      type: 'IDENTITY_LIST_IDENTITIES_SUCCESS',
      result: { items: [] },
    });

    expect(after.data).toEqual([{ id: 'dex' }]);
  });

  it('is not put into a loading state by the other request', () => {
    // The pending half belongs to somebody else's request; reacting to it
    // would flicker these buttons on every identities refresh.
    const loaded = loginProviders(undefined, {
      type: 'IDENTITY_LIST_LOGIN_PROVIDERS_SUCCESS',
      result: { items: [{ id: 'dex' }] },
    });

    const after = loginProviders(loaded, {
      type: 'IDENTITY_LIST_IDENTITIES_PENDING',
    });

    expect(after.data).toEqual([{ id: 'dex' }]);
    expect(after.loading).toBe(false);
  });

  it('ignores actions belonging to something else', () => {
    const state = loginProviders(undefined, { type: 'SOMETHING_ELSE' });

    expect(state.data).toEqual([]);
  });
});

describe('providerLogin', () => {
  it('clears the previous URL while a new attempt is pending', () => {
    const loaded = providerLogin(undefined, {
      type: `${START_PROVIDER_LOGIN}_SUCCESS`,
      result: { provider: 'dex', authorize_url: 'https://idp/one' },
    });

    const pending = providerLogin(loaded, {
      type: `${START_PROVIDER_LOGIN}_PENDING`,
    });

    // Leaving the old URL in place would send the browser to the previous
    // attempt's authorize URL, whose state has already been consumed.
    expect(pending.data).toBeNull();
    expect(pending.loading).toBe(true);
  });

  it('keeps the authorize URL on success', () => {
    const state = providerLogin(undefined, {
      type: `${START_PROVIDER_LOGIN}_SUCCESS`,
      result: { provider: 'dex', authorize_url: 'https://idp/auth' },
    });

    expect(state.data?.authorize_url).toBe('https://idp/auth');
  });
});

describe('identityCallback', () => {
  it('keeps the token and came_from', () => {
    const state = identityCallback(undefined, {
      type: `${COMPLETE_CALLBACK}_SUCCESS`,
      result: { token: 'jwt-value', came_from: '/somewhere' },
    });

    expect(state.data?.token).toBe('jwt-value');
    expect(state.data?.came_from).toBe('/somewhere');
  });

  it('marks a refusal as an error rather than a token', () => {
    const state = identityCallback(undefined, {
      type: `${COMPLETE_CALLBACK}_FAIL`,
      error: { status: 401 },
    });

    expect(state.data).toBeNull();
    expect(state.error).toEqual({ status: 401 });
  });
});
