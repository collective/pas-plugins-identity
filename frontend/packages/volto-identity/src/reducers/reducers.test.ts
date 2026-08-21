import { describe, expect, it } from 'vitest';

import {
  COMPLETE_CALLBACK,
  GET_MY_PROFILE,
  LIST_LOGIN_PROVIDERS,
  SEND_MAGIC_LINK,
  START_PROVIDER_LOGIN,
} from '../constants/ActionTypes';
import {
  identityCallback,
  loginProviders,
  myProfile,
  magicLinkSend,
  providerLogin,
} from './index';

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

describe('magicLinkSend', () => {
  it('records that a link went out', () => {
    const state = magicLinkSend(undefined, {
      type: `${SEND_MAGIC_LINK}_SUCCESS`,
      result: { sent: true },
    });

    expect(state.data).toBe(true);
  });

  it('does not treat a rate-limited refusal as sent', () => {
    const state = magicLinkSend(undefined, {
      type: `${SEND_MAGIC_LINK}_FAIL`,
      error: { status: 429 },
    });

    expect(state.data).toBe(false);
    expect(state.error).toEqual({ status: 429 });
  });
});

describe('myProfile', () => {
  it('starts with nothing known', () => {
    const state = myProfile(undefined, { type: 'INIT' });

    expect(state.data).toBeNull();
    expect(state.loaded).toBe(false);
  });

  it('keeps the whole answer', () => {
    const result = {
      '@id': '/@my-profile',
      userid: 'alice',
      profile: '/identity-profiles/alice',
      review_state: 'incomplete',
    };

    const state = myProfile(undefined, {
      type: `${GET_MY_PROFILE}_SUCCESS`,
      result,
    });

    expect(state.data).toEqual(result);
    expect(state.loaded).toBe(true);
  });

  it('records a failure without pretending it loaded', () => {
    const state = myProfile(undefined, {
      type: `${GET_MY_PROFILE}_FAIL`,
      error: 'nope',
    });

    expect(state.error).toBe('nope');
    expect(state.loaded).toBe(false);
  });
});
