/**
 * Reducers for a group's membership.
 * @module reducers/groups
 */

import { LIST_GROUP_MEMBERS } from '../constants/ActionTypes';
import type { GroupMembers } from '../types';
import { requestReducer } from './factory';

export const groupMembers = requestReducer<GroupMembers | null>(
  LIST_GROUP_MEMBERS,
  (result) => result ?? null,
  null,
);
