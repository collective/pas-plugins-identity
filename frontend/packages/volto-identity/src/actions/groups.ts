/**
 * Actions for a group's membership.
 * @module actions/groups
 */

import { LIST_GROUP_MEMBERS } from '../constants/ActionTypes';

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
  const search = query ? `?query=${encodeURIComponent(query)}` : '';
  return {
    type: LIST_GROUP_MEMBERS,
    request: {
      op: 'get',
      path: `/@group-members/${encodeURIComponent(groupId)}${search}`,
    },
  };
}
