/**
 * Actions for a group's membership.
 * @module actions/groups
 */

import {
  LIST_GROUP_MEMBERS,
  SEARCH_GROUP_MEMBERS,
} from '../constants/ActionTypes';
import { endpoints } from '@plone-collective/identity-core';

/**
 * Build the request for `@group-members/<id>`.
 *
 * @param groupId The group to read.
 * @param query Case-insensitive substring, matched against name and login.
 * @returns The request half of an action.
 */
function groupMembersRequest(groupId: string, query: string) {
  return {
    op: 'get',
    path: endpoints.groupMembers(groupId, query),
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
    request: groupMembersRequest(groupId, query),
  };
}

/**
 * Search the members of one group.
 *
 * The same endpoint as `listGroupMembers`, answered into a store slot of its
 * own. A request clears its slot while it is pending, and a group page keeps
 * its counts and its nesting on screen while somebody types -- so the search
 * cannot share the slot that holds them.
 *
 * @param groupId The group to search.
 * @param query Case-insensitive substring, matched against name and login.
 */
export function searchGroupMembers(groupId: string, query: string) {
  return {
    type: SEARCH_GROUP_MEMBERS,
    request: groupMembersRequest(groupId, query),
  };
}
