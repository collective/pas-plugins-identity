import { describe, expect, it } from 'vitest';

import { GET_MY_PROFILE } from '../constants/ActionTypes';
import { myProfile, userProfile } from './profile';

describe('userProfile', () => {
  it('starts empty', () => {
    const state = userProfile(undefined, { type: 'INIT' });

    expect(state.data).toBeNull();
    expect(state.loaded).toBe(false);
  });

  it('keeps the whole user, not a chosen few fields', () => {
    // The toolbar wants the portrait, the menu wants profile_url and an
    // administrator view wants identities and source; picking here would
    // mean editing this reducer every time one of them grows.
    const result = {
      id: 'alice',
      portrait: '/portrait.png',
      profile_url: '/identity-profiles/alice',
      source: 'identity_profile',
      identities: [],
    };

    const state = userProfile(undefined, {
      type: 'IDENTITY_GET_USER_PROFILE_SUCCESS',
      result,
    });

    expect(state.data).toEqual(result);
  });

  it('reports a failure rather than holding a stale user', () => {
    const loaded = userProfile(undefined, {
      type: 'IDENTITY_GET_USER_PROFILE_SUCCESS',
      result: { id: 'alice' },
    });

    const failed = userProfile(loaded, {
      type: 'IDENTITY_GET_USER_PROFILE_FAIL',
      error: 'boom',
    });

    expect(failed.error).toBe('boom');
    expect(failed.data).toBeNull();
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
