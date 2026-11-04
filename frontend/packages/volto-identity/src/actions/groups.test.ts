import { describe, expect, it } from 'vitest';

import {
  listDirectGroupMembers,
  listGroupMembers,
  searchGroupMembers,
  unnestGroup,
} from './groups';

describe('a group membership', () => {
  it('reads the summary unpaged', () => {
    expect(listGroupMembers('staff').request).toEqual({
      op: 'get',
      path: '/@group-members/staff',
    });
  });

  it('reads the first page in tens, the way plone.restapi pages', () => {
    expect(searchGroupMembers('staff').request.path).toBe(
      '/@group-members/staff?b_size=10',
    );
  });

  it('starts a later page where the one before ended', () => {
    expect(searchGroupMembers('staff', '', 4).request.path).toBe(
      '/@group-members/staff?b_size=10&b_start=30',
    );
  });

  it('searches within the page', () => {
    expect(searchGroupMembers('staff', 'ali bob').request.path).toBe(
      '/@group-members/staff?query=ali+bob&b_size=10',
    );
  });

  it('reads direct members for managing them', () => {
    expect(listDirectGroupMembers('staff', '', 2).request.path).toBe(
      '/@group-members/staff?direct=1&b_size=10&b_start=10',
    );
  });

  it('escapes the group id', () => {
    expect(listGroupMembers('a/b').request.path).toBe('/@group-members/a%2Fb');
  });

  it('un-nests a group by writing its own memberships', () => {
    expect(
      unnestGroup('/identity-profiles/developers', ['everyone']).request,
    ).toEqual({
      op: 'patch',
      path: '/identity-profiles/developers',
      data: { group_ids: ['everyone'] },
    });
  });
});
