/**
 * Reducers for the drivers a provider can be configured against.
 * @module reducers/drivers
 */

import { LIST_DRIVERS } from '../constants/ActionTypes';
import type { Driver } from '../types';
import { requestReducer } from './factory';

export const identityDrivers = requestReducer<Driver[]>(
  LIST_DRIVERS,
  (result) => result?.items ?? [],
  [],
);
