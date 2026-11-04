/**
 * Reducers for a group's membership.
 * @module reducers/groups
 */

import {
  LIST_DIRECT_GROUP_MEMBERS,
  LIST_GROUP_MEMBERS,
  SEARCH_GROUP_MEMBERS,
  UNNEST_GROUP,
} from '../constants/ActionTypes';
import type { GroupMembers } from '../types';
import { requestReducer } from './factory';

export const groupMembers = requestReducer<GroupMembers | null>(
  LIST_GROUP_MEMBERS,
  (result) => result ?? null,
  null,
);

/** A page of one group's members, kept apart from the group's summary. */
export const groupMemberSearch = requestReducer<GroupMembers | null>(
  SEARCH_GROUP_MEMBERS,
  (result) => result ?? null,
  null,
);

/** A page of what a change of one group's members acts on. */
export const groupDirectMembers = requestReducer<GroupMembers | null>(
  LIST_DIRECT_GROUP_MEMBERS,
  (result) => result ?? null,
  null,
);

/** Taking a nested group out of another; nothing to keep but the outcome. */
export const groupUnnest = requestReducer<null>(UNNEST_GROUP, () => null, null);
