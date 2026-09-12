import { describe, expect, it } from 'vitest';

import {
  confirmEmail,
  getMyProfile,
  getUserProfile,
  setPreferredEmail,
} from './profile';

describe('confirmEmail', () => {
  it('posts the one address to the confirmation endpoint', () => {
    // One address, not the list: the backend does the reordering, and
    // refuses an address that is not one of the caller's verified ones.
    expect(confirmEmail('alice@example.org').request).toEqual({
      op: 'post',
      path: '/@confirm-email',
      data: { email: 'alice@example.org' },
    });
  });
});

describe('getUserProfile', () => {
  it("reads Plone's own user endpoint", () => {
    // Not an endpoint of this package's own: the serializer adds fields to
    // the one Plone already serves rather than inventing a parallel view.
    expect(getUserProfile('alice').request.path).toBe('/@users/alice');
  });
});

describe('getMyProfile', () => {
  it('reads the routing endpoint', () => {
    expect(getMyProfile().request).toEqual({
      op: 'get',
      path: '/@my-profile',
    });
  });
});

describe('setPreferredEmail', () => {
  it('patches the profile with the whole list', () => {
    // The whole list, because `emails` is a field: a PATCH carrying one
    // address would replace the list with it rather than move it.
    expect(
      setPreferredEmail('/identity-profiles/alice', [
        'alice@example.org',
        'alice@example.com',
      ]).request,
    ).toEqual({
      op: 'patch',
      path: '/identity-profiles/alice',
      data: { emails: ['alice@example.org', 'alice@example.com'] },
    });
  });
});
