import { describe, expect, it } from 'vitest';

import { GET_USER_ACCOUNT } from '../constants/ActionTypes';
import { getUserAccount } from './account';

describe('getUserAccount', () => {
  it('asks for one account', () => {
    expect(getUserAccount('alice')).toEqual({
      type: GET_USER_ACCOUNT,
      request: { op: 'get', path: '/@user-account/alice' },
    });
  });

  it('asks for as many events as it is told to', () => {
    expect(getUserAccount('alice', 100).request.path).toBe(
      '/@user-account/alice?events=100',
    );
  });

  it('keeps a userid one path segment', () => {
    // A userid may be an email address, or anything a provider sent.
    expect(getUserAccount('a/b@example.com').request.path).toBe(
      '/@user-account/a%2Fb%40example.com',
    );
  });
});
