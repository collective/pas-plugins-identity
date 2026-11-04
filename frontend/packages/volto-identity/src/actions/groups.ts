/**
 * Actions for a group's membership.
 *
 * Reading goes through this add-on's `@group-members/<id>`. Changing goes
 * through plone.restapi's own endpoints, with Volto's own `updateGroup` for
 * people and for nesting a group: this add-on adds no endpoint to write a
 * membership. The one exception is un-nesting a group, which `PATCH
 * @groups/<id>` cannot do -- see `unnestGroup`.
 * @module actions/groups
 */

import {
  LIST_DIRECT_GROUP_MEMBERS,
  LIST_GROUP_MEMBERS,
  SEARCH_GROUP_MEMBERS,
  UNNEST_GROUP,
} from '../constants/ActionTypes';

/** How many members a page of a group's membership shows. */
export const MEMBERS_PAGE_SIZE = 10;

interface MembersRequestOptions {
  /** Case-insensitive substring, matched against name and login. */
  query?: string;
  /** The page to read, counted from 1. Unpaged when not given. */
  page?: number;
  /** Direct members only, nested groups included as rows. */
  direct?: boolean;
}

/**
 * Build the request for `@group-members/<id>`.
 *
 * Paged the way plone.restapi pages everything, with `b_size` and `b_start`.
 *
 * @param groupId The group to read.
 * @param options What to read.
 * @returns The request half of an action.
 */
function groupMembersRequest(
  groupId: string,
  { query = '', page, direct = false }: MembersRequestOptions = {},
) {
  const params = new URLSearchParams();
  if (query) {
    params.set('query', query);
  }
  if (direct) {
    params.set('direct', '1');
  }
  if (page !== undefined) {
    params.set('b_size', String(MEMBERS_PAGE_SIZE));
    if (page > 1) {
      params.set('b_start', String((page - 1) * MEMBERS_PAGE_SIZE));
    }
  }
  const search = params.toString();
  return {
    op: 'get',
    path: `/@group-members/${encodeURIComponent(groupId)}${
      search ? `?${search}` : ''
    }`,
  };
}

/**
 * List the members of one group, nested memberships included.
 *
 * plone.restapi's `@groups/<id>` already carries member userids and already
 * sees the nesting; what it cannot do is name each person, search within the
 * group, or say what feeds into it. This does all three.
 *
 * @param groupId The group to read.
 * @param query Case-insensitive substring, matched against name and login.
 */
export function listGroupMembers(groupId: string, query = '') {
  return {
    type: LIST_GROUP_MEMBERS,
    request: groupMembersRequest(groupId, { query }),
  };
}

/**
 * Read one page of the members of one group, optionally searched.
 *
 * The same endpoint as `listGroupMembers`, answered into a store slot of its
 * own. A request clears its slot while it is pending, and a group page keeps
 * its counts and its nesting on screen while somebody types or pages -- so
 * the listing cannot share the slot that holds them.
 *
 * @param groupId The group to read.
 * @param query Case-insensitive substring, matched against name and login.
 * @param page The page to read, counted from 1.
 */
export function searchGroupMembers(groupId: string, query = '', page = 1) {
  return {
    type: SEARCH_GROUP_MEMBERS,
    request: groupMembersRequest(groupId, { query, page }),
  };
}

/**
 * Read one page of what a change of members acts on.
 *
 * The groups nested in this one through their own field, then the people in
 * this group itself -- not the people who arrive through a nested group,
 * who are removed from that group instead.
 *
 * @param groupId The group to read.
 * @param query Case-insensitive substring, matched against name and login.
 * @param page The page to read, counted from 1.
 */
export function listDirectGroupMembers(groupId: string, query = '', page = 1) {
  return {
    type: LIST_DIRECT_GROUP_MEMBERS,
    request: groupMembersRequest(groupId, { query, page, direct: true }),
  };
}

/**
 * Take a nested group out of the group it is in.
 *
 * `PATCH @groups/<id>` removes only what PlonePAS lists as the group's
 * members, and that list holds userids: a nested group is never in it, so
 * asking plone.restapi to remove one changes nothing. The nesting is stored
 * on the inner group, as its own `group_ids`, so this writes that field on
 * the inner group's content -- the same request its edit form sends.
 *
 * @param groupUrl The nested group's own URL.
 * @param groupIds The groups it stays in.
 */
export function unnestGroup(groupUrl: string, groupIds: string[]) {
  return {
    type: UNNEST_GROUP,
    request: {
      op: 'patch',
      path: groupUrl,
      data: { group_ids: groupIds },
    },
  };
}
